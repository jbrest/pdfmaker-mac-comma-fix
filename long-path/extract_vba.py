#!/usr/bin/env python3
"""Write the standard modules of your own copy of linkCreation.dotm to .bas files.

usage: extract_vba.py <linkCreation.dotm> <output-folder>

Needs oletools (pip install oletools). Writes the code modules only (link, utils, webLinkCreation,
intraDocLinkCreation, bookmarks); the document class and the progress form are skipped.
The output is Adobe's code from your own installation: keep it on your machine.
"""

import sys
from pathlib import Path

from oletools.olevba import VBA_Parser

SKIP = {"ThisDocument", "progressDialog"}


def main(src, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parser = VBA_Parser(src)
    if not parser.detect_vba_macros():
        sys.exit("No VBA project found.")
    for _file, _stream, vba_filename, code in parser.extract_macros():
        name = Path(vba_filename).stem
        if name in SKIP or not code.strip():
            continue
        text = code.replace("\r\n", "\n").replace("\n", "\r\n")
        (out / f"{name}.bas").write_bytes(text.encode("latin-1", "replace"))
        print("wrote", out / f"{name}.bas")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
