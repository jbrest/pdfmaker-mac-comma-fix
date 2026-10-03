#!/usr/bin/env python3
"""Map a SharePoint/OneDrive document URL to its synced local file.

usage: resolve_cloud_path.py <url>

Exit 0 and print the local path when exactly one distinct file matches.
Exit 2: no match.  Exit 3: ambiguous (two or more distinct files).  Exit 4: bad input.

Rule: after https://<tenant>.sharepoint.com/(sites|teams)/<site>/ the remaining URL segments
are split into <library name>/<relative path>, trying the shortest library name (longest
relative path) first. A split matches when <library folder>/<relative path> is an existing
file under ~/Library/CloudStorage/OneDrive-*/, where the library folder name (letters and
digits only, lowercase) contains the site name (same normalisation). For /personal/ URLs the
library is the OneDrive root itself. The first split with any match decides; distinct
real paths (symlinks resolved) at that split must number exactly one.
"""

import os
import re
import sys
from urllib.parse import unquote, urlparse


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def candidate_roots(home, site, personal):
    base = os.path.join(home, "Library", "CloudStorage")
    roots = []
    try:
        tops = sorted(d for d in os.listdir(base) if d.startswith("OneDrive-"))
    except OSError:
        return roots
    for top in tops:
        top_path = os.path.join(base, top)
        if personal:
            roots.append(top_path)
            continue
        try:
            kids = sorted(os.listdir(top_path))
        except OSError:
            continue
        for kid in kids:
            kid_path = os.path.join(top_path, kid)
            if os.path.isdir(kid_path) and norm(site) and norm(site) in norm(kid):
                roots.append(kid_path)
    return roots


def resolve(url, home):
    parts = urlparse(url.strip())
    if parts.scheme != "https" or not parts.netloc.lower().endswith(".sharepoint.com"):
        return 4, None
    raw = [s for s in parts.path.split("/") if s]
    decoded = [unquote(s) for s in raw]
    if len(raw) < 4 or decoded[0].lower() not in ("sites", "teams", "personal"):
        return 4, None
    if any(s in (".", "..") or "\x00" in s or "/" in s for s in decoded + raw):
        return 4, None
    personal = decoded[0].lower() == "personal"
    site = decoded[1]
    roots = candidate_roots(home, site, personal)
    for k in range(1, len(raw) - 2):  # library = segments[2:2+k]; relative path = the rest
        rels = {os.path.join(*raw[2 + k:]), os.path.join(*decoded[2 + k:])}
        found = set()
        for root in roots:
            for rel in rels:
                p = os.path.join(root, rel)
                if os.path.isfile(p):
                    found.add(os.path.realpath(p))
        if len(found) == 1:
            return 0, found.pop()
        if len(found) > 1:
            return 3, None
    return 2, None


def main(argv):
    if len(argv) != 2:
        return 4
    code, path = resolve(argv[1], os.path.expanduser("~"))
    if path:
        sys.stdout.write(path)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
