# Adobe PDFMaker comma filename fix for macOS

Adobe PDFMaker for Microsoft Word on macOS can raise VBA run-time error 5 when a document path contains a comma:

> Invalid procedure call or argument

The failure occurs because Adobe's `AcrobatUtils.scpt` receives multiple values in one comma-delimited string. It splits on every comma and assumes the first field is the complete path. A valid path such as:

```text
/Documents/Lease, Bressert & Van Raalten.docx
```

is therefore truncated to `/Documents/Lease`.

This repository contains an independent patcher and tests. It does **not** include or redistribute Adobe's script, VBA project, or other Adobe files.

## Tested configuration

- macOS 26.6.2
- Microsoft Word 16.113.2
- Adobe Acrobat Pro 26.002.21901
- Vulnerable `AcrobatUtils.scpt` SHA-256: `de6d7a302b6dbf9e10d5da66ac20386fc3c2400963fc34efabe6823ab2d674d7`

Other releases may use the same implementation. The patcher refuses to modify an unfamiliar script.

## What the patch changes

The original parser treats the payload as:

```text
filePath,workflowToken,isSharepointFile[,appType]
```

The fix locates Adobe's known workflow token from the right and rejoins every preceding field with commas. The filename remains unchanged.

## Inspect without changing anything

Quit Microsoft Word, clone this repository, and run:

```bash
python3 patch_pdfmaker.py status
```

Possible states are:

- `vulnerable`: the known defective parser was found.
- `patched`: this fix is already installed.
- `unsupported`: the script differs from the tested implementation and will not be modified.

## Install

Quit Microsoft Word, then run:

```bash
python3 patch_pdfmaker.py apply
```

The patcher:

1. Decompiles the installed helper with Apple's `osadecompile`.
2. Verifies that it matches the known vulnerable parser.
3. Inserts the comma-safe parser.
4. Recompiles it with Apple's `osacompile`.
5. Validates the result.
6. Creates a timestamped backup beside the installed helper.
7. Atomically installs the patched helper.

Restart Word and retry PDFMaker with a comma in the filename.

## Roll back

Quit Word and run:

```bash
python3 patch_pdfmaker.py rollback
```

This restores the newest backup created by the patcher and preserves a copy of the currently installed helper.

To choose a specific backup:

```bash
python3 patch_pdfmaker.py rollback --backup "/path/to/AcrobatUtils.scpt.backup-YYYYMMDD-HHMMSS"
```

## Updates

An Acrobat update may replace `AcrobatUtils.scpt`. Run `status` again if the failure returns. Do not blindly reapply the patch to an unknown Adobe version; open an issue and include the status output instead.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

The tests include actual AppleScript execution on macOS for filenames containing one comma, multiple commas, and Adobe's optional fourth parameter.

## Scope and disclaimer

This is an unofficial interoperability fix and is not affiliated with or endorsed by Adobe. It modifies only the per-user helper at:

```text
~/Library/Application Scripts/com.microsoft.Word/AcrobatUtils.scpt
```

Use it on systems you control. Keep the generated backup. Adobe trademarks and product names belong to their respective owners.
