"""Per-commit decision: which test numbers to run.

Submission #1 rules:
  R1  every changed file is a .py whose AST is unchanged (comments, blank
      lines, formatting)  -> run nothing.
  *   anything else -> run every test.
"""

from __future__ import annotations

import ast
import zipfile
from pathlib import Path

from selector import patch as patchlib


def ast_dump(source: bytes) -> str | None:
    try:
        return ast.dump(ast.parse(source), include_attributes=False)
    except (SyntaxError, ValueError):
        return None


class Decider:
    def __init__(self, tests: list[dict], maps: Path, log) -> None:
        self.log = log
        self.all = {t["number"] for t in tests}
        self.src = zipfile.ZipFile(maps / "src.zip")
        self.src_names = set(self.src.namelist())

    def original(self, path: str) -> bytes | None:
        if path in self.src_names:
            return self.src.read(path)
        return None

    def decide(self, text: str) -> tuple[set[int], str]:
        if not text.strip():
            return set(), "empty patch"
        files = patchlib.parse(text)
        if not files:
            return set(self.all), "unparsed patch"
        for fp in files:
            if fp.binary or fp.renamed or fp.is_add or fp.is_delete or not fp.path.endswith(".py"):
                return set(self.all), f"non-py or structural change: {fp.path}"
            old = self.original(fp.path)
            if old is None:
                return set(self.all), f"unknown file {fp.path}"
            new = patchlib.apply(old.decode("utf-8"), fp).encode("utf-8")
            before, after = ast_dump(old), ast_dump(new)
            if before is None or after is None or before != after:
                return set(self.all), f"code change in {fp.path}"
        return set(), "AST unchanged"
