from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "long-path"))

import resolve_cloud_path as r  # noqa: E402

URL = "https://example.sharepoint.com/sites/Shared%20Drive/Shared%20Documents/Deals/Entity%20A/Memo,%20final.docx"


def touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cs = self.home / "Library" / "CloudStorage" / "OneDrive-Example"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_resolves_library_folder_with_different_name(self) -> None:
        f = self.cs / "Sharepoint - Shared Drive - Documents" / "Deals" / "Entity A" / "Memo, final.docx"
        touch(f)
        self.assertEqual(r.resolve(URL, str(self.home)), (0, os.path.realpath(f)))

    def test_no_match(self) -> None:
        (self.cs / "Sharepoint - Shared Drive - Documents").mkdir(parents=True)
        self.assertEqual(r.resolve(URL, str(self.home)), (2, None))

    def test_ambiguous_same_split(self) -> None:
        for lib in ("Shared Drive - Documents", "Shared Drive - Archive"):
            touch(self.cs / lib / "Deals" / "Entity A" / "Memo, final.docx")
        self.assertEqual(r.resolve(URL, str(self.home)), (3, None))

    def test_site_name_must_match_folder(self) -> None:
        touch(self.cs / "Other Site - Documents" / "Deals" / "Entity A" / "Memo, final.docx")
        self.assertEqual(r.resolve(URL, str(self.home)), (2, None))

    def test_nonsharepoint_and_malformed_urls(self) -> None:
        for bad in ("http://example.sharepoint.com/sites/a/b/c.docx",
                    "https://example.com/sites/a/b/c.docx",
                    "https://example.sharepoint.com/sites/a/b",
                    "https://example.sharepoint.com/other/a/b/c.docx",
                    "https://example.sharepoint.com/sites/a/b/%2E%2E/c.docx",
                    "https://example.sharepoint.com/sites/a/b/..%2F../c.docx"):
            self.assertEqual(r.resolve(bad, str(self.home)), (4, None), bad)

    def test_personal_library_is_onedrive_root(self) -> None:
        f = self.cs / "Folder" / "Doc.docx"
        touch(f)
        url = "https://example-my.sharepoint.com/personal/jo_example_com/Documents/Folder/Doc.docx"
        self.assertEqual(r.resolve(url, str(self.home)), (0, os.path.realpath(f)))

    def test_symlink_duplicates_count_once(self) -> None:
        real = self.cs / "Shared Drive - Documents" / "Deals" / "Entity A" / "Memo, final.docx"
        touch(real)
        (self.cs / "Shared Drive - Mirror").symlink_to(self.cs / "Shared Drive - Documents")
        self.assertEqual(r.resolve(URL, str(self.home)), (0, os.path.realpath(real)))

    def test_missing_cloudstorage_folder(self) -> None:
        self.assertEqual(r.resolve(URL, str(self.home)), (2, None))


if __name__ == "__main__":
    unittest.main()
