#!/usr/bin/env python3
"""Build a private AppleScript helper, AcrobatUtilsLP.scpt, for a separate Word add-in.

apply   -> decompiles the installed AcrobatUtils.scpt, appends a ResolveCloudDocPath handler,
           compiles the result as AcrobatUtilsLP.scpt beside it and installs
           resolve_cloud_path.py there too. Adobe's AcrobatUtils.scpt is not modified.
           Works on the original helper or on one already patched by patch_pdfmaker.py
           (the comma-in-filename fix); a note is printed if that fix is absent.
remove  -> deletes AcrobatUtilsLP.scpt and resolve_cloud_path.py.

Quit Word before running either command.
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

DIR = Path.home() / "Library" / "Application Scripts" / "com.microsoft.Word"
ADOBE = DIR / "AcrobatUtils.scpt"
LP = DIR / "AcrobatUtilsLP.scpt"
RESOLVER_DST = DIR / "resolve_cloud_path.py"
RESOLVER_SRC = Path(__file__).resolve().parent / "resolve_cloud_path.py"
FIX_MARKER = "PDFMAKER_COMMA_FIX_V1"
TAG = "-- PDFMAKER_CLOUD_RESOLVE_V1"

HANDLER = f"""
{TAG}
-- Maps a SharePoint/OneDrive document URL to its synced local file.
-- Returns the local POSIX path, or "" when there is no unique match.
on ResolveCloudDocPath(docURL)
	try
		set scriptPath to (POSIX path of (path to library folder from user domain)) & "Application Scripts/com.microsoft.Word/resolve_cloud_path.py"
		return do shell script "/usr/bin/python3 " & quoted form of scriptPath & " " & quoted form of docURL
	on error
		return ""
	end try
end ResolveCloudDocPath
"""


def run(cmd):
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"Error: {' '.join(cmd)}\n{r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def word_running():
    return subprocess.run(["/usr/bin/pgrep", "-x", "Microsoft Word"], capture_output=True).returncode == 0


def apply():
    if word_running():
        sys.exit("Quit Microsoft Word first.")
    if LP.exists():
        sys.exit(f"{LP} already exists; run remove first.")
    if not ADOBE.is_file():
        sys.exit(f"{ADOBE} not found.")
    if not RESOLVER_SRC.is_file():
        sys.exit(f"Missing {RESOLVER_SRC}")
    source = run(["/usr/bin/osadecompile", str(ADOBE)])
    if "on ConvertToPDF(" not in source:
        sys.exit("The installed helper does not look like Adobe's PDFMaker helper; nothing changed.")
    patched = source if TAG in source else source.rstrip("\n") + "\n" + HANDLER
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "a.applescript"
        out = Path(d) / "AcrobatUtilsLP.scpt"
        src.write_text(patched, encoding="utf-8")
        run(["/usr/bin/osacompile", "-o", str(out), str(src)])
        if TAG not in run(["/usr/bin/osadecompile", str(out)]):
            sys.exit("Compiled result lacks the handler; nothing changed.")
        shutil.copy2(out, LP)
        os.chmod(LP, stat.S_IMODE(ADOBE.stat().st_mode))
    shutil.copy2(RESOLVER_SRC, RESOLVER_DST)
    os.chmod(RESOLVER_DST, 0o644)
    print("Created", LP)
    print("Installed", RESOLVER_DST)
    if FIX_MARKER not in source:
        print("Note: the comma-in-filename fix is not present in the helper this was built from.")


def remove():
    if word_running():
        sys.exit("Quit Microsoft Word first.")
    for p in (LP, RESOLVER_DST):
        if p.exists():
            p.unlink()
            print("Removed", p)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["apply", "remove"])
    {"apply": apply, "remove": remove}[ap.parse_args().command]()
