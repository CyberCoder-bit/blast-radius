"""Write maps/src.zip: the pinned sqlglot Python sources the selector diffs against.

    python3 tools/snapshot_src.py vendor/sqlglot maps/src.zip

Holds sqlglot/**/*.py and tests/**/*.py at commit eb11aec (no fixtures). It is
committed so the image needs no network at build time.
"""

import sys
import zipfile
from pathlib import Path


def main(root: Path, out: Path) -> None:
    count = 0
    with zipfile.ZipFile(out, "w") as archive:
        for sub in ("sqlglot", "tests"):
            for path in sorted((root / sub).rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                info = zipfile.ZipInfo(str(path.relative_to(root)), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes(), compresslevel=9)
                count += 1
    print(f"wrote {count} files to {out}", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
