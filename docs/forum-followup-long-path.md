# Follow-up comment for the comma-fix thread

Follow-up: a second Mac problem in the same ribbon, VBA run-time error 9105 (“String is longer than 255 characters”).

It happens when the open document is in SharePoint or OneDrive and its URL path is long. The same document in a local folder converts fine, even with a path over 300 characters, so the length of the file name isn’t the issue. In the cloud branch of the add-in, Word for Mac reports the document path as the URL-encoded SharePoint address, and the add-in passes it to `Documents.Add(Template:=…)`. Word rejects that argument above 255 characters. Encoding makes the string longer than the address you see: in my case a 252-character URL was 266 characters once encoded.

The workaround that worked for me: a second add-in, with its own name and ribbon tab (“Acrobat (LongPath)”), identical to Adobe’s except that, for cloud documents whose encoded path is over 240 characters, it looks up the synced copy of the file under ~/Library/CloudStorage/OneDrive-… and converts that as an ordinary local file. If it can’t find exactly one match it falls back to Adobe’s normal behaviour. Short paths never touch the new code. Adobe’s add-in is left in place (renamed so there’s only one tab), and the new add-in uses its own AppleScript helper, so an Acrobat update doesn’t overwrite it.

I haven’t published Adobe’s code and won’t. The repo has the helper scripts, tests, and a step-by-step guide for building the add-in from your own copy of linkCreation.dotm: https://github.com/jbrest/pdfmaker-mac-comma-fix/tree/main/long-path

Caveats: tested on one Mac ([add Word, Acrobat and macOS versions]); the file has to be synced locally, and the first time through, macOS asks whether Word may access OneDrive-managed files. In my testing that prompt appeared once and didn’t return on later conversions. If the synced copy isn’t on disk yet (a file you just renamed or created, say), the add-in falls back to Adobe’s route and you get 9105 again; wait for OneDrive to finish syncing. Comma filenames convert correctly through the new add-in. This is an unofficial workaround.

It would be better if Adobe fixed this in the add-in itself. Ideally the cloud branch would stop passing the URL to `Documents.Add`, and the helper would stop splitting its argument on commas. If anyone at Adobe reads this thread, those two changes would remove both bugs.
