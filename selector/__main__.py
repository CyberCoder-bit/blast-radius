"""Entry point: `python -m selector`.

Reads /data/commits/*.patch and /data/tests.json (or $BLAST_DATA for local
runs) and prints one JSON answer line per commit to stdout. Logs go to stderr.
Any failure while analysing one commit falls back to running every test for
that commit, so the run itself never fails.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

from selector.decide import Decider
from selector.schedule import schedule

DATA = Path(os.environ.get("BLAST_DATA", "/data"))
MAPS = Path(os.environ.get("BLAST_MAPS", Path(__file__).resolve().parent.parent / "maps"))


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def main() -> None:
    tests = json.loads((DATA / "tests.json").read_text())["tests"]
    duration_ms = {t["number"]: int(t["seconds"] * 1000 + 0.5) for t in tests}
    all_numbers = sorted(duration_ms)
    decider = Decider(tests, MAPS, log)

    lines = []
    for patch in sorted((DATA / "commits").glob("*.patch")):
        commit = patch.stem
        try:
            selected, why = decider.decide(patch.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            log(f"{commit}: error, running everything\n{traceback.format_exc()}")
            selected, why = set(all_numbers), "error"
        workers = schedule(sorted(selected), duration_ms)
        load = max((sum(duration_ms[n] for n in w) for w in workers), default=0)
        log(f"{commit}: {len(selected)} tests, {len(workers)} workers, max {load} ms [{why}]")
        lines.append(json.dumps({"commit": commit, "workers": workers}, separators=(",", ":")))
    sys.stdout.write("".join(line + "\n" for line in lines))


if __name__ == "__main__":
    main()
