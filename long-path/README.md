# Acrobat PDFMaker in Word for Mac: run-time error 9105 on long SharePoint paths

Acrobat's Word ribbon on macOS can fail with VBA run-time error 9105, "String is longer than 255 characters", when the open document lives in SharePoint or OneDrive and its URL path is long. Short paths convert normally. A document in an ordinary local folder converts even with a path of 300+ characters.

## Cause

For a cloud document, the add-in builds `ActiveDocument.path & "/" & name`. In Word for Mac that path is the URL-encoded SharePoint address. The add-in then passes it to `Documents.Add(Template:=...)`, and Word limits that argument to 255 characters. Percent-encoding makes the string longer than the path you see on screen: a 252-character decoded URL was 266 characters encoded.

## What this does

Adobe's add-in is left alone. You build a second, separate add-in with its own name and ribbon tab, "Acrobat (LongPath)". It is identical to Adobe's except for one edit: when the document is a cloud document and the encoded path is longer than 240 characters, the add-in asks a helper script for the synced local file under `~/Library/CloudStorage/OneDrive-*/` and converts that file as an ordinary local document. If no unique local file is found, it falls back to Adobe's original behaviour. Short paths never reach the new code.

The mapping from a SharePoint URL to a local folder is not stored anywhere I could find, so `resolve_cloud_path.py` infers it. It takes the URL after `/sites/<site>/` and tries each split into library name and relative path, shortest library name first, looking for `<library folder>/<relative path>` under a OneDrive folder whose name contains the site name. The first split that finds a file decides. If one split finds two different files, it refuses and the add-in falls back. See the docstring for the exact rule and `tests/test_resolve_cloud_path.py` for the cases.

Limits:
- The file must be synced to the Mac. The first time Word reads a file this way, macOS asks whether Word may access files managed by OneDrive, and the conversion needs that permission. In testing the prompt appeared once and did not come back on later conversions; expect the same, though macOS can ask again after a OneDrive or system update.
- If the synced copy isn't on disk yet (a file just created, renamed or moved in SharePoint, or OneDrive still syncing), nothing resolves and the add-in falls back to Adobe's behaviour, which fails with the same 9105 error. Wait for OneDrive to finish and try again.
- This repository does not contain Adobe's VBA. You extract it from your own installation (step 2) and must not redistribute the resulting `.dotm`.
- Tested on one Mac. Versions: see the forum post.

## Build it

You need Python 3 (the macOS one is fine), Word for Mac, and an Adobe Acrobat installation that put `linkCreation.dotm` in Word's startup folder.

1. **Helper.** Quit Word and run `python3 install_longpath_helper.py apply`. This compiles `AcrobatUtilsLP.scpt` from your installed `AcrobatUtils.scpt` (adding a `ResolveCloudDocPath` handler) and installs `resolve_cloud_path.py` next to it, both in `~/Library/Application Scripts/com.microsoft.Word/`. Adobe's helper is not modified. If you use `patch_pdfmaker.py` for the comma fix, apply that first and the new helper will include it.

2. **Extract the modules.** In a virtual environment run `pip install oletools`, then `python3 extract_vba.py "/Library/Application Support/Microsoft/Office365/User Content.localized/Startup/Word/linkCreation.dotm" ./vba_source`. This writes `link.bas`, `utils.bas`, `webLinkCreation.bas`, `intraDocLinkCreation.bas` and `bookmarks.bas`. (Word for Mac hides Adobe's locked project in the VBA editor, so the editor can't be used for this.)

3. **Empty template.** Run `python3 make_ribbon_template.py ribbon_base.dotm` and open the result in Word. It holds only the ribbon XML.

4. **Import.** Open the VBA editor (Tools > Macro > Visual Basic Editor), select the template's project, and use File > Import File for each of the five `.bas` files. The progress-dialog form and `ThisDocument` are not needed: current Word for Mac uses a native progress window from Adobe's framework.

5. **The one edit.** In module `link`, sub `startPrintService`, apply the change described in `startPrintService_edit.txt`.

6. **Rename the helper reference.** Click inside a code window, choose Edit > Replace, set the scope to Current Project, and replace `AcrobatUtils.scpt` with `AcrobatUtilsLP.scpt` everywhere (13 occurrences). Replace All.

7. **Project name and compile.** Tools > Properties: set the project name to `AcrobatLongPath`. Debug > Compile should finish without a message.

8. **Install.** Save as a macro-enabled template (`.dotm`), named for example `linkCreation_longpath.dotm`, into `~/Library/Group Containers/UBF8T346G9.Office/User Content.localized/Startup.localized/Word/`.

9. **Hide Adobe's tab.** Otherwise Word shows two Acrobat tabs. Rename Adobe's `linkCreation.dotm` in `/Library/Application Support/Microsoft/Office365/User Content.localized/Startup/Word/` to `linkCreation.dotm.disabled` (this needs `sudo`).

10. Quit and reopen Word. The "Acrobat (LongPath)" tab appears. To test, open a SharePoint document with a long path and choose Create PDF, cloud.

## Undo

Delete the add-in from the personal Startup folder, rename Adobe's file back, and run `python3 install_longpath_helper.py remove`.

## Updates

The new add-in has its own helper and doesn't depend on Adobe's file names, so an Acrobat update won't overwrite it. It still calls Adobe's `MacPDFMLoader.framework`, so a major Acrobat release that changes that framework could break it.

This is an unofficial workaround and is not affiliated with or endorsed by Adobe. Adobe trademarks and product names belong to their respective owners.
