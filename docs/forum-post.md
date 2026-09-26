# Forum post

## Title

Fix for Acrobat PDFMaker run-time error 5 when a Word filename contains a comma on Mac

## Post

I found a reproducible filename bug in Acrobat PDFMaker for Microsoft Word on macOS.

If the Word document's path contains a comma, choosing Acrobat and then Create PDF can produce VBA run-time error 5: `Invalid procedure call or argument`. Removing the comma makes the same document convert normally.

The problem is in Adobe's installed `AcrobatUtils.scpt`. PDFMaker sends the path and several control values in one comma-delimited string. The helper splits on every comma and assumes the first field is the complete path, so a comma in a valid macOS filename corrupts the argument list.

I published an open-source patcher that repairs the parser locally without redistributing Adobe's files. It validates the installed version, creates a backup, recompiles the helper using Apple's own tools, and supports rollback. The repository also includes tests for one comma, multiple commas, and Adobe's optional fourth parameter.

Repository: REPLACE_WITH_GITHUB_URL

Tested with Adobe Acrobat Pro 26.002.21901, Word 16.113.2, and macOS 26.6.2. This is an unofficial workaround; an Acrobat update may overwrite the helper.
