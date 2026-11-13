"""Restore pinned evidence from an authorized copy of the corrected release."""
import argparse
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RELEASE_SHA256 = "a8a01afb5f9193a710562019d2eb774871fb8a5d68b34366bd86eac4584346d1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    args = parser.parse_args()
    if sha256(args.release.read_bytes()).hexdigest() != RELEASE_SHA256:
        parser.error("corrected release SHA-256 mismatch")
    files = {}
    with ZipFile(args.release) as archive:
        for line in (ROOT / "EVIDENCE_SHA256.txt").read_text(encoding="utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT):
                parser.error(f"invalid evidence destination: {relative}")
            data = archive.read(f"terrapulse-developer-a/{relative}")
            if sha256(data).hexdigest() != expected:
                parser.error(f"evidence SHA-256 mismatch: {relative}")
            if path.exists() and path.read_bytes() != data:
                parser.error(f"existing evidence differs: {relative}")
            files[path] = data
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
    print(f"Verified and restored {len(files)} local evidence files")


if __name__ == "__main__":
    main()
