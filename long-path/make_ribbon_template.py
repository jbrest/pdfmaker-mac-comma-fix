#!/usr/bin/env python3
"""Create an empty macro-enabled Word template that carries only the ribbon XML.

usage: make_ribbon_template.py <output.dotm>

Open the result in Word, import the modules in the VBA editor, rename the VBA project and save
it as a .dotm (File > Save As) into Word's Startup folder.
"""

import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.ms-word.template.macroEnabledTemplate.main+xml"/></Types>'
)
RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.microsoft.com/office/2007/relationships/ui/extensibility" Target="customUI/customUI14.xml"/>'
    "</Relationships>"
)
DOCUMENT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body><w:p/><w:sectPr/></w:body></w:document>"
)


def main(out):
    ribbon = (HERE / "ribbon" / "customUI14.xml").read_text(encoding="utf-8")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", DOCUMENT)
        z.writestr("customUI/customUI14.xml", ribbon)
    print("wrote", out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
