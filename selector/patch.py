"""Unified-diff parsing and application.

parse() splits a patch into FilePatch objects. apply() rebuilds the new file
text from the original and verifies every context/removed line, so a patch
that does not match the pinned sources raises instead of guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(Exception):
    pass


@dataclass
class Hunk:
    old_start: int
    old_len: int
    new_start: int
    new_len: int
    lines: list[str]


@dataclass
class FilePatch:
    old_path: str | None = None  # None means /dev/null (file added)
    new_path: str | None = None  # None means /dev/null (file deleted)
    hunks: list[Hunk] = field(default_factory=list)
    binary: bool = False
    renamed: bool = False
    mode_change: bool = False
    header_seen: bool = False

    @property
    def path(self) -> str:
        return self.old_path or self.new_path or ""

    @property
    def is_add(self) -> bool:
        return self.old_path is None

    @property
    def is_delete(self) -> bool:
        return self.new_path is None


def _strip(path: str) -> str | None:
    path = path.split("\t", 1)[0].strip()
    if path == "/dev/null":
        return None
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    if path[:2] in ("a/", "b/"):
        path = path[2:]
    return path


def parse(text: str) -> list[FilePatch]:
    files: list[FilePatch] = []
    cur: FilePatch | None = None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i].rstrip("\r")
        if line.startswith("diff --git "):
            cur = FilePatch()
            files.append(cur)
            m = re.match(r"diff --git (\S+) (\S+)$", line)
            if m:
                cur.old_path, cur.new_path = _strip(m.group(1)), _strip(m.group(2))
        elif line.startswith("--- ") and i + 1 < n and lines[i + 1].startswith("+++ "):
            if cur is None or cur.header_seen:
                cur = FilePatch()
                files.append(cur)
            cur.old_path = _strip(line[4:])
            cur.new_path = _strip(lines[i + 1].rstrip("\r")[4:])
            cur.header_seen = True
            i += 2
            continue
        elif line.startswith("@@"):
            m = _HUNK.match(line)
            if not m or cur is None:
                raise PatchError(f"bad hunk header: {line[:60]!r}")
            old_start, new_start = int(m.group(1)), int(m.group(3))
            old_len = 1 if m.group(2) is None else int(m.group(2))
            new_len = 1 if m.group(4) is None else int(m.group(4))
            body: list[str] = []
            i += 1
            rem_old, rem_new = old_len, new_len
            while i < n and (rem_old > 0 or rem_new > 0):
                b = lines[i].rstrip("\r")
                tag = b[:1]
                if tag == "\\":
                    body.append(b)
                elif tag == " " or b == "":
                    rem_old -= 1
                    rem_new -= 1
                    body.append(b if b else " ")
                elif tag == "-":
                    rem_old -= 1
                    body.append(b)
                elif tag == "+":
                    rem_new -= 1
                    body.append(b)
                else:
                    break
                i += 1
            while i < n and lines[i].startswith("\\"):
                body.append(lines[i])
                i += 1
            if rem_old != 0 or rem_new != 0:
                raise PatchError("truncated hunk")
            cur.hunks.append(Hunk(old_start, old_len, new_start, new_len, body))
            continue
        elif cur is not None:
            if line.startswith("new file mode"):
                cur.old_path = None
            elif line.startswith("deleted file mode"):
                cur.new_path = None
            elif line.startswith("rename from ") or line.startswith("copy from "):
                cur.renamed = True
                cur.old_path = line.split(" ", 2)[2]
            elif line.startswith("rename to ") or line.startswith("copy to "):
                cur.renamed = True
                cur.new_path = line.split(" ", 2)[2]
            elif line.startswith("Binary files") or line.startswith("GIT binary patch"):
                cur.binary = True
            elif line.startswith("old mode") or line.startswith("new mode"):
                cur.mode_change = True
        i += 1
    return files


@dataclass
class Changes:
    """Line-level view of one file's hunks."""

    removed: set[int]  # old line numbers removed or modified
    added: set[int]  # new line numbers added or modified
    insert_after: set[int]  # old line numbers that a pure insertion follows (0 = top)


def changes(fp: FilePatch) -> Changes:
    removed: set[int] = set()
    added: set[int] = set()
    insert_after: set[int] = set()
    for h in fp.hunks:
        old_ln = h.old_start if h.old_len else h.old_start + 1
        new_ln = h.new_start if h.new_len else h.new_start + 1
        for b in h.lines:
            tag = b[:1]
            if tag == " ":
                old_ln += 1
                new_ln += 1
            elif tag == "-":
                removed.add(old_ln)
                old_ln += 1
            elif tag == "+":
                added.add(new_ln)
                insert_after.add(old_ln - 1)
                new_ln += 1
    return Changes(removed, added, insert_after)


def apply(old_text: str, fp: FilePatch) -> str:
    old = old_text.splitlines(keepends=True)
    out: list[str] = []
    pos = 0  # index into old
    for h in fp.hunks:
        start = h.old_start - 1 if h.old_len else h.old_start
        if start < pos or start > len(old):
            raise PatchError("hunk out of range")
        out.extend(old[pos:start])
        pos = start
        for b in h.lines:
            tag, content = b[:1], b[1:]
            if tag == "\\":
                if out and out[-1].endswith("\n"):
                    out[-1] = out[-1][:-1]
                continue
            if tag in (" ", "-"):
                if pos >= len(old) or old[pos].rstrip("\r\n") != content.rstrip("\r"):
                    raise PatchError("context mismatch")
                if tag == " ":
                    out.append(old[pos])
                pos += 1
            elif tag == "+":
                out.append(content + "\n")
    out.extend(old[pos:])
    return "".join(out)
