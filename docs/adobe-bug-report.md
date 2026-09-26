# Adobe bug report

## Title

PDFMaker for Word on macOS fails when the document path contains a comma

## Product and environment

- Adobe Acrobat Pro 26.002.21901
- Microsoft Word 16.113.2
- macOS 26.6.2

## Reproduction

1. Save a Word document with a comma in its filename, such as `Lease, Example.docx`.
2. In Word, choose Acrobat and then Create PDF.
3. PDFMaker raises VBA run-time error 5: `Invalid procedure call or argument`.
4. Rename the same file to remove the comma and repeat. Conversion succeeds.

## Root cause

The installed Word helper `AcrobatUtils.scpt` passes conversion arguments as:

```text
filePath,workflowToken,isSharepointFile[,appType]
```

`ConvertToPDF` sets AppleScript's text item delimiter to a comma, splits the complete payload, and assigns the first item to `filePath`. Any comma in the path therefore shifts the remaining fields and corrupts both the path and workflow arguments.

## Recommended correction

Replace the delimiter-based transport with structured arguments. For backward compatibility, the current payload can be parsed by locating the known workflow token from the right and reconstructing all preceding comma-separated fields as the path.

The issue was reproduced against an `AcrobatUtils.scpt` with SHA-256:

```text
de6d7a302b6dbf9e10d5da66ac20386fc3c2400963fc34efabe6823ab2d674d7
```

An independently tested patch and reproduction tests are available in this repository.
