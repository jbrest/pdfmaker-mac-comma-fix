#!/usr/bin/env python3
"""Patch Adobe PDFMaker for macOS so file paths may contain commas."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime


DEFAULT_SCRIPT = (
    Path.home()
    / "Library"
    / "Application Scripts"
    / "com.microsoft.Word"
    / "AcrobatUtils.scpt"
)

MARKER = "-- PDFMAKER_COMMA_FIX_V1"
CONVERT_HANDLER = "on ConvertToPDF(inputParams)"

PARSER_HANDLER = r'''-- PDFMAKER_COMMA_FIX_V1
-- Adobe passes filePath,workflowToken,isSharepointFile[,appType] as one string.
-- Paths may contain commas, so locate the workflow token from the right and
-- reconstruct every preceding field as the original path.
on PDFMakerCommaFixParse(inputParams)
	set savedDelimiters to AppleScript's text item delimiters
	try
		set AppleScript's text item delimiters to ","
		set paramList to text items of inputParams
		set AppleScript's text item delimiters to savedDelimiters

		if (count of paramList) < 3 then return {}
		set workflowTokens to {"macpdfm", "macpdfmAndShare", "macpdfmAndSign", "macpdfmShowIPM", "macpdfmFreemiumConvert"}
		set workflowIndex to 0
		repeat with paramIndex from ((count of paramList) - 1) to 2 by -1
			set candidateToken to item paramIndex of paramList as text
			if workflowTokens contains candidateToken then
				set workflowIndex to paramIndex
				exit repeat
			end if
		end repeat
		if workflowIndex is 0 then return {}

		set filePathParts to items 1 thru (workflowIndex - 1) of paramList
		set AppleScript's text item delimiters to ","
		set filePath to filePathParts as text
		set AppleScript's text item delimiters to savedDelimiters

		set workflowToken to item workflowIndex of paramList as text
		set isSharepointFileStr to item (workflowIndex + 1) of paramList as text
		set appType to ""
		if (count of paramList) > (workflowIndex + 1) then
			set appType to item (workflowIndex + 2) of paramList as text
		end if
		return {filePath, workflowToken, isSharepointFileStr, appType}
	on error
		set AppleScript's text item delimiters to savedDelimiters
		return {}
	end try
end PDFMakerCommaFixParse
'''

REPLACEMENT_BLOCK = r'''	-- PDFMAKER_COMMA_FIX_V1
	set parsedParams to my PDFMakerCommaFixParse(inputParams)
	if (count of parsedParams) < 4 then
		return
	end if
	set filePath to item 1 of parsedParams
	set workflowToken to item 2 of parsedParams
	set isSharepointFileStr to item 3 of parsedParams
	set appType to item 4 of parsedParams

'''

VULNERABLE_SIGNALS = (
    'set AppleScript\'s text item delimiters to ","',
    "set paramList to text items of inputParams",
    "set filePath to item 1 of paramList",
    "set workflowToken to item 2 of paramList",
)

LEGACY_PATCH_SIGNALS = (
    "on ParseConvertParams(inputParams)",
    "set parsedParams to my ParseConvertParams(inputParams)",
)


class PatchError(RuntimeError):
    """Raised when the installed helper cannot be patched safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise PatchError(f"Command failed: {' '.join(command)}\n{details}")
    return result


def decompile_script(path: Path) -> str:
    if not path.is_file():
        raise PatchError(f"Adobe helper not found: {path}")
    return run_checked(["/usr/bin/osadecompile", str(path)]).stdout


def detect_status(source: str) -> str:
    if MARKER in source:
        return "patched"
    # Recognize the manually installed prototype that preceded this patcher.
    if all(signal in source for signal in LEGACY_PATCH_SIGNALS):
        return "patched"
    if CONVERT_HANDLER in source and all(signal in source for signal in VULNERABLE_SIGNALS):
        return "vulnerable"
    return "unsupported"


def patch_source(source: str) -> tuple[str, bool]:
    status = detect_status(source)
    if status == "patched":
        return source, False
    if status != "vulnerable":
        raise PatchError(
            "This AcrobatUtils.scpt version does not match the known vulnerable "
            "implementation. No changes were made."
        )

    handler_start = source.index(CONVERT_HANDLER)
    handler_body_start = source.index("\n", handler_start) + 1
    sharepoint_match = re.search(
        r"(?m)^[ \t]*set isSharepointFile to\b",
        source[handler_body_start:],
    )
    if sharepoint_match is None:
        raise PatchError("Could not locate the expected PDFMaker parser boundary.")
    parser_end = handler_body_start + sharepoint_match.start()

    old_parser = source[handler_body_start:parser_end]
    if not all(signal in old_parser for signal in VULNERABLE_SIGNALS):
        raise PatchError("The parser differs from the tested Adobe implementation.")

    input_comment = source.rfind("\n# Input:", 0, handler_start)
    insert_at = input_comment + 1 if input_comment >= 0 else handler_start

    with_handler = source[:insert_at] + PARSER_HANDLER + "\n" + source[insert_at:]
    shift = len(PARSER_HANDLER) + 1
    handler_body_start += shift
    parser_end += shift

    patched = (
        with_handler[:handler_body_start]
        + REPLACEMENT_BLOCK
        + with_handler[parser_end:]
    )
    if detect_status(patched) != "patched":
        raise PatchError("Internal validation failed while constructing the patch.")
    return patched, True


def word_is_running() -> bool:
    result = subprocess.run(
        ["/usr/bin/pgrep", "-x", "Microsoft Word"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def compile_and_validate(source: str, destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="pdfmaker-comma-fix-") as temp_dir:
        source_path = Path(temp_dir) / "AcrobatUtils.applescript"
        source_path.write_text(source, encoding="utf-8")
        run_checked(
            [
                "/usr/bin/osacompile",
                "-o",
                str(destination),
                str(source_path),
            ]
        )
    compiled_source = decompile_script(destination)
    if MARKER not in compiled_source:
        raise PatchError("The compiled helper did not retain the patch marker.")


def apply_patch(script_path: Path) -> Path | None:
    if word_is_running():
        raise PatchError("Quit Microsoft Word before applying the patch.")

    source = decompile_script(script_path)
    patched_source, changed = patch_source(source)
    if not changed:
        return None

    original_mode = stat.S_IMODE(script_path.stat().st_mode)
    backup_path = script_path.with_name(
        f"{script_path.name}.backup-{timestamp()}"
    )

    with tempfile.TemporaryDirectory(prefix="pdfmaker-comma-fix-") as temp_dir:
        compiled_path = Path(temp_dir) / "AcrobatUtils.scpt"
        compile_and_validate(patched_source, compiled_path)

        shutil.copy2(script_path, backup_path)
        replacement_path = script_path.with_name(
            f".{script_path.name}.replacement-{timestamp()}"
        )
        shutil.copy2(compiled_path, replacement_path)
        os.chmod(replacement_path, original_mode)
        os.replace(replacement_path, script_path)

    if detect_status(decompile_script(script_path)) != "patched":
        raise PatchError(
            f"Post-install validation failed. Restore the backup at {backup_path}."
        )
    return backup_path


def find_backups(script_path: Path) -> list[Path]:
    pattern = f"{script_path.name}.backup-*"
    return sorted(script_path.parent.glob(pattern), reverse=True)


def rollback(script_path: Path, backup_path: Path | None = None) -> tuple[Path, Path]:
    if word_is_running():
        raise PatchError("Quit Microsoft Word before rolling back the patch.")
    if not script_path.is_file():
        raise PatchError(f"Adobe helper not found: {script_path}")

    if backup_path is None:
        backups = find_backups(script_path)
        if not backups:
            raise PatchError("No PDFMaker comma-fix backup was found.")
        backup_path = backups[0]
    if not backup_path.is_file():
        raise PatchError(f"Backup not found: {backup_path}")

    safety_copy = script_path.with_name(
        f"{script_path.name}.pre-rollback-{timestamp()}"
    )
    shutil.copy2(script_path, safety_copy)
    replacement_path = script_path.with_name(
        f".{script_path.name}.rollback-{timestamp()}"
    )
    shutil.copy2(backup_path, replacement_path)
    os.replace(replacement_path, script_path)
    return backup_path, safety_copy


def print_status(script_path: Path) -> None:
    source = decompile_script(script_path)
    print(f"Script: {script_path}")
    print(f"SHA-256: {sha256_file(script_path)}")
    print(f"Status: {detect_status(source)}")
    backups = find_backups(script_path)
    if backups:
        print(f"Newest backup: {backups[0]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repair Adobe PDFMaker's comma-in-path parser on macOS."
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=DEFAULT_SCRIPT,
        help=f"AcrobatUtils.scpt path (default: {DEFAULT_SCRIPT})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Inspect the installed helper without changing it.")
    subparsers.add_parser("apply", help="Back up and patch the installed helper.")
    rollback_parser = subparsers.add_parser(
        "rollback", help="Restore the newest backup created by this tool."
    )
    rollback_parser.add_argument(
        "--backup",
        type=Path,
        help="Restore a specific backup instead of the newest one.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    script_path = args.script.expanduser().resolve()
    try:
        if args.command == "status":
            print_status(script_path)
        elif args.command == "apply":
            backup = apply_patch(script_path)
            if backup is None:
                print("PDFMaker is already patched; no changes were made.")
            else:
                print("Patch installed successfully.")
                print(f"Backup: {backup}")
                print("Restart Word, then retry a filename containing a comma.")
        elif args.command == "rollback":
            requested_backup = args.backup.expanduser().resolve() if args.backup else None
            restored, safety_copy = rollback(script_path, requested_backup)
            print(f"Restored: {restored}")
            print(f"Pre-rollback copy: {safety_copy}")
        return 0
    except PatchError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
