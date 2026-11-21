#!/usr/bin/env python3
"""Install a fixed, unmodified BOOTSTRA.386 v5 distribution for the site.

Only the web assets required by this Eleventy site are extracted. Their bytes
are not patched or recompiled. The upstream ZIP is pinned to a Git commit and
verified against its Git blob object ID before use.
"""
from __future__ import annotations

import hashlib
import io
import json
import pathlib
import re
import shutil
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent.parent
OUT = HERE / "src" / "assets" / "vendor" / "bootstra386"
UPSTREAM = "https://raw.githubusercontent.com/kristopolous/BOOTSTRA.386"
COMMIT = "3af1895e7212f36566d4d46e867e8c4073528e8f"
ZIP_NAME = "bootstra.386-latest-v5.zip"
ZIP_BLOB = "0536a1f3b9872afeb95c660461d223c941057edc"
MARKER = OUT / "source.json"


def get(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "deskmate-reference-site/0.1"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def select(members: list[str], suffix: str) -> str:
    matches = [m for m in members if m.endswith("/" + suffix) or m == suffix]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one upstream {suffix}, got {matches!r}. Archive entries: {members[:80]!r}")
    return matches[0]


def install() -> None:
    if MARKER.is_file():
        try:
            data = json.loads(MARKER.read_text(encoding="utf-8"))
            required = [OUT / p for p in data["files"]]
            if data["commit"] == COMMIT and data["zip_git_blob"] == ZIP_BLOB and all(p.is_file() for p in required):
                print("Pinned BOOTSTRA.386 assets already present")
                return
        except (ValueError, OSError, KeyError, TypeError):
            pass

    payload = get(f"{UPSTREAM}/{COMMIT}/{ZIP_NAME}")
    actual = hashlib.sha1(
        b"blob " + str(len(payload)).encode() + b"\0" + payload
    ).hexdigest()
    if actual != ZIP_BLOB:
        raise RuntimeError(f"Upstream archive changed: {actual} != {ZIP_BLOB}")

    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        mapping = {}
        for relative in (
            "dist/css/bootstrap.min.css",
            "dist/js/bootstrap.bundle.min.js",
            "dist/js/bootstrap-386.js",
        ):
            # Published ZIPs may omit the source-tree dist/ prefix.
            source = select(names, relative.removeprefix("dist/"))
            mapping[relative.removeprefix("dist/")] = z.read(source)

        css = mapping["css/bootstrap.min.css"].decode("utf-8")
        references = set(re.findall(r"url\(\s*['\"]?\.\./fonts/([^'\"\)]+)", css))
        if not references:
            raise RuntimeError("Upstream stylesheet contains no font or glyph references")
        for name in sorted(references):
            if "/" in name or name in (".", ".."):
                raise RuntimeError(f"Unexpected font asset name: {name}")
            source = select(names, "fonts/" + name)
            mapping["fonts/" + name] = z.read(source)

    mapping["LICENSE-BOOTSTRA386.txt"] = get(f"{UPSTREAM}/{COMMIT}/LICENSE")
    mapping["LICENSE-BOOTSTRAP.txt"] = get(f"{UPSTREAM}/{COMMIT}/v5.3.1/LICENSE")
    mapping["ATTRIBUTION.txt"] = (
        "BOOTSTRA.386 v5.3.1 by the BOOTSTRA.386 contributors.\n"
        "Theme upstream: https://github.com/kristopolous/BOOTSTRA.386\n"
        "The BOOTSTRA.386 repository is Apache License 2.0; underlying\n"
        "Bootstrap code is MIT. See accompanying license files.\n"
        "Px437_IBM_EGA8.otf and derived glyph images are based on the\n"
        "Oldschool PC Font Pack by VileR, CC BY-SA 4.0:\n"
        "https://int10h.org/oldschool-pc-fonts/readme/\n"
        "https://creativecommons.org/licenses/by-sa/4.0/\n"
        "These third-party rights are not changed by our site integration.\n"
    ).encode("utf-8")

    # All extracted asset bytes are copied without modification.
    if OUT.exists():
        shutil.rmtree(OUT)
    for relative, payload in mapping.items():
        destination = OUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    manifest = {
        "project": "kristopolous/BOOTSTRA.386",
        "version": "5.3.1",
        "commit": COMMIT,
        "zip_git_blob": ZIP_BLOB,
        "files": sorted(mapping),
    }
    MARKER.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Installed unmodified BOOTSTRA.386: {len(mapping)} files")


if __name__ == "__main__":
    install()
