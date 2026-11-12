"""skilldesc's description lines of a classic port, moved onto D2R's line functions after the table merge.

A line is a function number plus text a/b and calc a/b (descline1 + desctexta1, ...). A classic skill's rows keep the
classic functions, which print the classic text and then the value ("Duration: " 40 " seconds"); D2R's strings carry the
value's format code instead ("Duration: %d seconds"), so the merged line prints both. A line clashes when
- a text names a D2R string with a format code in a column, under a function, that D2R's own lines never use it in;
- it has no text under a function D2R's lines never use (a built-in that picks its label from the skill); or
- a text's string has a format code under a function and column D2R's lines never format (D2R's classic functions print
  text raw, "+%d Percent ...").
Each clashing line is rewritten onto D2R's functions by the project's `Mapping`; strings stay D2R's. A clash left after
the rewrite fails the merge (`rewrite` raises ValueError naming the lines the mapping cannot place).

The mapping is the project's decision (which classic function becomes which D2R function), so it is passed in, never
part of the toolkit. `Mapping` fields:
    lines     classic function -> (D2R function, how, calc). `how`: "d2r" lays text a/b out as a D2R line of that function
              lays the key out; "swap" is text b, then text a (format, then skill name); "b" is text b alone; "copy" is the
              skill's own D2R line naming the key, calcs included (D2R function and calc are None). `calc(a, b)` rebuilds
              calc a/b from the classic ones
    fixed     (classic function, text a) -> the whole line [function, text a, text b, calc a, calc b]; a calc of None keeps
              the classic calc a
    keys      classic function -> {classic string key: the D2R key that took its place with another layout}
    builtins  classic function -> {skill element (skills EType, "" any): D2R label} for lines with no text (the game picks
              the label from the skill): the skill's own D2R line with one of the function's labels is copied, else D2R's
              most common line with the element's label; no label for the element leaves the line empty
    below     classic function -> D2R label of the line D2R prints under that built-in: put in the built-in's slot, the
              lines above it moving up one (the tooltip stacks lines upward)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .ids import Table

LINE = re.compile(r"^(desc|dsc2|dsc3)line(\d+)$")
CODE = re.compile(r"%(\+?\d*(\.\d+)?[diufs]|%)")  # not "2% per": a classic literal percent sign

Calc = Callable[[str, str], "tuple[str, str]"]


@dataclass
class Mapping:
    """The project's classic-function -> D2R-function mapping (fields in the module docstring)."""
    lines: dict[str, tuple[str | None, str, Calc | None]] = field(default_factory=dict)
    fixed: dict[tuple[str, str], tuple] = field(default_factory=dict)
    keys: dict[str, dict[str, str]] = field(default_factory=dict)
    builtins: dict[str, dict[str, str]] = field(default_factory=dict)
    below: dict[str, str] = field(default_factory=dict)


def hide_off_tree(t: Table) -> None:
    """SkillPage 0 for each row the source keeps out of the tree (SkillRow 0): a classic client hides those, D2R draws
    them in the page's first cell."""
    col = {c.lower(): j for j, c in enumerate(t.header)}
    page, row = col["skillpage"], col["skillrow"]
    for r in t.rows:
        if r[row] in ("", "0"):
            r[page] = "0"


def texts(*roots: Path) -> dict[str, str]:
    """String key -> English text, later roots overriding earlier ones."""
    out = {}
    for root in roots:
        for f in sorted((root / "local" / "lng" / "strings").glob("*.json")):
            out |= {e["Key"]: e.get("enUS", "") for e in json.loads(f.read_text("utf-8-sig"))}
    return out


def formatted(d2r_data: Path) -> set[str]:
    """D2R's string keys whose English text has a format code."""
    return {k for k, v in texts(d2r_data).items() if "%" in v}


def lines(t: Table) -> list[tuple[int, int, list[int]]]:
    """(row, line column, [text a, text b, calc a, calc b] columns) for every non-empty line."""
    col = {c: j for j, c in enumerate(t.header)}
    out = []
    for j, c in enumerate(t.header):
        if m := LINE.match(c):
            p, n = m.groups()
            parts = [col[f"{p}{s}{n}"] for s in ("texta", "textb", "calca", "calcb")]
            out += [(i, j, parts) for i, r in enumerate(t.rows) if r[j]]
    return out


def layouts(d2r: Table, fmt: set[str]) -> Counter:
    """(key, function, column 0/1) -> how often D2R's lines use it, and (function, key, text a, text b) -> how often."""
    seen: Counter = Counter()
    for i, j, (a, b, _, _) in lines(d2r):
        r = d2r.rows[i]
        for k, col in ((r[a], 0), (r[b], 1)):
            if k in fmt:
                seen[(k, r[j], col)] += 1
                seen[(r[j], k, r[a], r[b])] += 1
    return seen


def clashes(t: Table, d2r: Table, fmt: set[str], strings: dict[str, str] | None = None) -> list[str]:
    """The lines D2R's game would print wrongly: "skill column function text a text b". `strings`: the merged strings
    (key -> English), for format codes in strings D2R never uses in skilldesc."""
    strings = strings or {}
    seen = layouts(d2r, fmt)
    used = {k[0] for k in seen if len(k) == 3}
    formats = {k[1:] for k in seen if len(k) == 3}  # (function, column) D2R's lines format
    funcs = {d2r.rows[i][j] for i, j, _ in lines(d2r)}

    def wrong(k: str, f: str, col: int) -> bool:
        if k in used:
            return (k, f, col) not in seen
        text = strings.get(k, "")
        return bool(CODE.search(text)) != ((f, col) in formats) and "%" in text

    out = []
    for i, j, (a, b, _, _) in lines(t):
        r = t.rows[i]
        if (r[j] not in funcs and not r[a]) or any(wrong(k, r[j], col) for k, col in ((r[a], 0), (r[b], 1))):
            out.append(f"{r[0]} {t.header[j]} {r[j]} {r[a]} {r[b]}")
    return out


def rewrite(t: Table, d2r: Table, fmt: set[str], mapping: Mapping, elements: dict[str, str] | None = None,
            strings: dict[str, str] | None = None) -> None:
    """Rewrites t's clashing lines in place by `mapping`; raises ValueError naming lines it can't place. `elements`:
    skilldesc name (lower case) -> the skill's EType, for `mapping.builtins`; `strings`: as for clashes."""
    elements = elements or {}
    seen = layouts(d2r, fmt)
    used = {k[0] for k in seen if len(k) == 3}
    bad = set(clashes(t, d2r, fmt, strings))
    d2r_lines = {}
    for i, j, parts in lines(d2r):
        d2r_lines.setdefault(d2r.rows[i][0].lower(), []).append([d2r.rows[i][j]] + [d2r.rows[i][p] for p in parts])
    missing, below = [], []
    for i, j, parts in lines(t):
        r = t.rows[i]
        f, a, b, ca, cb = r[j], *(r[p] for p in parts)
        if f"{r[0]} {t.header[j]} {f} {a} {b}" not in bad:
            continue
        key = mapping.keys.get(f, {}).get(a) or next((k for k in (a, b) if k in used), a)
        new = None
        if (f, a) in mapping.fixed:
            new = list(mapping.fixed[(f, a)])
            new[3] = ca if new[3] is None else new[3]
        elif f in mapping.builtins and not a:
            labels = mapping.builtins[f]
            label = labels.get(elements.get(r[0].lower(), ""), labels.get(""))
            own = [x for x in d2r_lines.get(r[0].lower(), []) if x[1] in labels.values()]
            common = Counter(tuple(x) for ls in d2r_lines.values() for x in ls if x[1] == label)
            new = own[0] if own else list(common.most_common(1)[0][0]) if common else [""] * 5
            if f in mapping.below:
                below.append((i, j, mapping.below[f]))
        elif f in mapping.lines:
            to, how, calc = mapping.lines[f]
            if how == "copy":  # a source-only skill takes D2R's most common line for the key
                common = Counter(tuple(x) for ls in d2r_lines.values() for x in ls if key in x[1:3])
                new = next((x for x in d2r_lines.get(r[0].lower(), []) if key in x[1:3]),
                           common and list(common.most_common(1)[0][0]))
            elif how == "swap":
                new = [to, b, a, *calc(ca, cb)]
            elif how == "b":
                new = [to, b, "", *calc(ca, cb)]
            else:
                # D2R's most used text a/b for the key under this function; a key only the source has stands alone
                ab = max(((k[2], k[3]) for k in seen if len(k) == 4 and k[:2] == (to, key)),
                         key=lambda x: seen[(to, key, *x)], default=None if key in used else (key, ""))
                new = ab and [to, *ab, *calc(ca, cb)]
        if new is None:
            missing.append(f"{r[0]} {t.header[j]} {f} {a} {b}")
            continue
        r[j], *vals = new
        for p, v in zip(parts, vals):
            r[p] = v
    for i, j, label in below:
        r = t.rows[i]
        if any(r[ps[0]] == label for k, _, ps in lines(t) if k == i):
            continue
        common = Counter(tuple(x) for ls in d2r_lines.values() for x in ls if x[1] == label)
        new = next((x for x in d2r_lines.get(r[0].lower(), []) if x[1] == label), common.most_common(1)[0][0])
        p, n = LINE.match(t.header[j]).groups()
        col = {c: k for k, c in enumerate(t.header)}
        last = max(int(m[2]) for c in t.header if (m := LINE.match(c)) and m[1] == p)
        slots = [[col[f"{p}{s}{k}"] for s in ("line", "texta", "textb", "calca", "calcb")] for k in range(int(n), last + 1)]
        if r[slots[-1][0]]:
            missing.append(f"{r[0]} {t.header[j]}: no free line for {label}")
            continue
        for lo, hi in reversed(list(zip(slots, slots[1:]))):
            for x, y in zip(lo, hi):
                r[y] = r[x]
        for x, v in zip(slots[0], new):
            r[x] = v
    if missing:
        raise ValueError(f"skilldesc lines with no D2R layout (add them to the mapping): {'; '.join(missing)}")
