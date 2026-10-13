"""Pack the repository into one self-contained script that recreates it anywhere.

    python scripts/make_bootstrap.py [-o dist/netcheat-bootstrap.py]

Packs every tracked and new (not ignored) file of the working tree. The generated script needs only
Python 3.9+ and no other files:

    python netcheat-bootstrap.py [target-dir] [--git]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
import textwrap
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

TEMPLATE = '''\
"""Recreate the netcheat repository ({count} files, generated from commit {commit}).

    python {name} [target-dir] [--git]

target-dir defaults to ./netcheat and must not exist or be empty. --git also runs git init and makes an
initial commit, ready to push to a new remote. Needs Python 3.9+ only.
"""
import argparse, base64, hashlib, io, json, subprocess, sys, zipfile
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Recreate the netcheat repository.")
    parser.add_argument("target", nargs="?", default="netcheat", help="folder to create (default: ./netcheat)")
    parser.add_argument("--git", action="store_true", help="git init and commit the files")
    args = parser.parse_args()
    target = Path(args.target)
    if target.exists() and any(target.iterdir()):
        sys.exit(f"{{target}} exists and is not empty, choose another folder")

    with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE))) as archive:
        for name in archive.namelist():
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != CHECKSUMS[name]:
                sys.exit(f"checksum mismatch for {{name}}: the script was damaged in transfer")
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(f"Created {{len(CHECKSUMS)}} files in {{target}}")

    if args.git:
        for command in (["init", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "Initial import of netcheat"]):
            subprocess.run(["git", *command], cwd=target, check=True)
        print("Git repository initialised. Next: git remote add origin <url> && git push -u origin main")
    print(f"Install: cd {{target}} && pip install -e .")


# Packed repository: a zip archive (base64) and the SHA-256 of every file, checked while unpacking.
CHECKSUMS = json.loads({checksums!r})
ARCHIVE = """
{archive}
"""

if __name__ == "__main__":
    main()
'''


def repository_files() -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPO, capture_output=True, check=True,
    ).stdout.decode()
    return sorted(name for name in output.split("\0") if name and (REPO / name).is_file())


def build(out: Path) -> int:
    files = repository_files()
    buffer, checksums = io.BytesIO(), {}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            data = (REPO / name).read_bytes()
            archive.writestr(name, data)
            checksums[name] = hashlib.sha256(data).hexdigest()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    script = TEMPLATE.format(
        count=len(files),
        commit=commit or "none",
        name=out.name,
        checksums=json.dumps(checksums, separators=(",", ":")),
        archive="\n".join(textwrap.wrap(base64.b64encode(buffer.getvalue()).decode(), 76)),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(script, encoding="utf-8")
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out", type=Path, default=REPO / "dist" / "netcheat-bootstrap.py")
    args = parser.parse_args()
    count = build(args.out)
    print(f"Packed {count} files into {args.out} ({args.out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
