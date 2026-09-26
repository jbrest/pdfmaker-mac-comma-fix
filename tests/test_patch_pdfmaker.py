from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

import patch_pdfmaker


VULNERABLE_SOURCE = r'''on SomethingElse()
	return true
end SomethingElse

# Input: filePath,workflowToken,isSharepointFile[,appType].
on ConvertToPDF(inputParams)
	#Parse params; reset delimiters immediately (session-global state).
	set AppleScript's text item delimiters to ","
	set paramList to text items of inputParams
	set AppleScript's text item delimiters to ""
	if (count of paramList) < 3 then
		return
	end if
	set filePath to item 1 of paramList
	set workflowToken to item 2 of paramList
	set isSharepointFileStr to item 3 of paramList
	set appType to ""
	if (count of paramList) >= 4 then
		set appType to item 4 of paramList
	end if

	set isSharepointFile to (isSharepointFileStr is equal to "true")
	return filePath
end ConvertToPDF
'''


class SourcePatchTests(unittest.TestCase):
    def test_detects_vulnerable_source(self) -> None:
        self.assertEqual(patch_pdfmaker.detect_status(VULNERABLE_SOURCE), "vulnerable")

    def test_patch_is_idempotent(self) -> None:
        patched, changed = patch_pdfmaker.patch_source(VULNERABLE_SOURCE)
        self.assertTrue(changed)
        self.assertEqual(patch_pdfmaker.detect_status(patched), "patched")
        patched_again, changed_again = patch_pdfmaker.patch_source(patched)
        self.assertFalse(changed_again)
        self.assertEqual(patched_again, patched)

    def test_unknown_source_is_rejected(self) -> None:
        with self.assertRaises(patch_pdfmaker.PatchError):
            patch_pdfmaker.patch_source("on ConvertToPDF(inputParams)\nend ConvertToPDF\n")

    def test_recognizes_manually_installed_prototype(self) -> None:
        prototype = """on ParseConvertParams(inputParams)
end ParseConvertParams
on ConvertToPDF(inputParams)
    set parsedParams to my ParseConvertParams(inputParams)
end ConvertToPDF
"""
        self.assertEqual(patch_pdfmaker.detect_status(prototype), "patched")


@unittest.skipUnless(Path("/usr/bin/osascript").exists(), "AppleScript requires macOS")
class AppleScriptParserTests(unittest.TestCase):
    def run_parser(self, input_params: str) -> list[str]:
        escaped = input_params.replace("\\", "\\\\").replace('"', '\\"')
        source = (
            patch_pdfmaker.PARSER_HANDLER
            + "\n"
            + f'set parsedParams to PDFMakerCommaFixParse("{escaped}")\n'
            + 'set AppleScript\'s text item delimiters to linefeed\n'
            + 'return parsedParams as text\n'
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "test.applescript"
            script_path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                ["/usr/bin/osascript", str(script_path)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.rstrip("\n").splitlines()

    def test_preserves_single_comma(self) -> None:
        parsed = self.run_parser(
            "/tmp/Lease, Bressert & Van Raalten.docx,macpdfm,false"
        )
        self.assertEqual(
            parsed,
            ["/tmp/Lease, Bressert & Van Raalten.docx", "macpdfm", "false"],
        )

    def test_preserves_multiple_commas(self) -> None:
        parsed = self.run_parser(
            "/tmp/one, two, three.docx,macpdfmAndShare,true"
        )
        self.assertEqual(
            parsed,
            ["/tmp/one, two, three.docx", "macpdfmAndShare", "true"],
        )

    def test_preserves_optional_app_type(self) -> None:
        parsed = self.run_parser(
            "/tmp/file.docx,macpdfmShowIPM,false,Word"
        )
        self.assertEqual(
            parsed,
            ["/tmp/file.docx", "macpdfmShowIPM", "false", "Word"],
        )


if __name__ == "__main__":
    unittest.main()
