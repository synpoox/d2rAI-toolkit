"""Check a deviation list: each "### Name (n)" heading's n matches the rows of the table under it.

A classic port keeps a markdown list of the ways the mod differs from its source (the deviation list that
shared/classic_import/diff.py's gate reads). Each section heading states its count, and a count that drifts from its
table is an edit that lost a row. Run it before a commit:

    py -3 tools/check_deviations.py [docs/deviations.md]

Exit 0 when every counted heading matches, 1 with one line per mismatch, 2 when the file is missing or has no counted
heading. `heading_counts(text)` is the parser (rows exclude the header and the separator).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def heading_counts(text: str) -> list[tuple[str, int, int]]:
    """(heading, stated count, table rows) for each counted heading."""
    out, current = [], None
    for line in text.splitlines():
        if line.startswith("#"):
            m = re.fullmatch(r"#+ (.*) \((\d+)\)", line.strip())
            current = [m.group(1), int(m.group(2)), -2] if m else None
            if current:
                out.append(current)
        elif current and line.startswith("|"):
            current[2] += 1
    return [(h, n, max(rows, 0)) for h, n, rows in out]


def mismatches(text: str) -> list[str]:
    """One line per heading whose stated count is not its row count."""
    return [f"{h} ({n}) has {rows} rows" for h, n, rows in heading_counts(text) if n != rows]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0] if args else "docs/deviations.md")
    if not path.is_file():
        print(f"check_deviations: no such file: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    if not heading_counts(text):
        print(f"check_deviations: {path} has no counted heading ('### Name (n)')", file=sys.stderr)
        return 2
    bad = mismatches(text)
    for line in bad:
        print(f"{path}: {line}")
    if not bad:
        print(f"check_deviations: OK, {len(heading_counts(text))} heading(s) in {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
