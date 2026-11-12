"""Changelog fragments: a PR adds a small file to changelog.d/ instead of editing CHANGELOG.md, so two PRs never conflict
on the same lines. The release folds the fragments into the changelog (templates/changelog.d/README.md has the format).

Python 3.12+, standard library only. Used by release/stage.py; importable on its own.
"""
from __future__ import annotations

import re
from pathlib import Path

FRAGMENTS_DIR = "changelog.d"
CHANGELOG = "CHANGELOG.md"


class ChangelogError(Exception):
    pass


def fold(changelog: str, version: str, fragments: list[str]) -> str:
    """The changelog with each fragment's bullet lines added at the end of the `### <version> (<date>)` section (else
    the `### Unreleased` one). A fragment may open with a `#### <Category>` line: its bullets then join that
    heading's bullets in the section, or start it. Fragments fold in the order given."""
    m = None
    for head in (rf"{re.escape(version)} \(.*?\)", "Unreleased"):  # the version's own section wins over Unreleased
        m = re.search(rf"^### {head}[ \t]*\n(.*?)(?=^### |\Z)", changelog, re.M | re.S)
        if m:
            break
    if not m:
        raise ChangelogError(f"{CHANGELOG} has no '### Unreleased' or '### {version} (<date>)' section")
    body = m.group(1)
    for text in fragments:
        lines = [ln for ln in text.strip().splitlines() if ln.strip()]
        head = lines.pop(0) if lines and lines[0].startswith("#### ") else None
        if not lines:
            continue
        add = "\n".join(lines)
        if head is None:
            body = body.rstrip("\n") + "\n" + add + "\n\n"
            continue
        h = re.search(rf"^{re.escape(head)}[ \t]*\n(.*?)(?=^#### |\Z)", body, re.M | re.S)
        if h:
            body = body[:h.start(1)] + h.group(1).rstrip("\n") + "\n" + add + "\n\n" + body[h.end(1):]
        else:
            body = body.rstrip("\n") + f"\n\n{head}\n\n{add}\n\n"
    return changelog[:m.start(1)] + body.rstrip("\n") + "\n\n" + changelog[m.end(1):]


def fragment_files(root: Path, fragments_dir: str = FRAGMENTS_DIR, changelog: str = CHANGELOG) -> list[Path]:
    """The fragments, by file name (the order they fold in). A README.md is documentation, not a fragment, and the
    changelog itself is never one."""
    log = (Path(root) / changelog).resolve()
    return sorted(p for p in (Path(root) / fragments_dir).glob("*.md")
                  if p.name.lower() != "readme.md" and p.resolve() != log)


def pending(root: Path, version: str, changelog: str = CHANGELOG, fragments_dir: str = FRAGMENTS_DIR) -> tuple[str, list[Path]]:
    """The changelog's text with the fragments folded in, and those files. Changes nothing on disk."""
    files = fragment_files(root, fragments_dir, changelog)
    try:
        text = (Path(root) / changelog).read_text("utf-8")
    except OSError as e:
        raise ChangelogError(f"cannot read the changelog: {e}")
    return (fold(text, version, [f.read_text("utf-8") for f in files]) if files else text), files


def fold_fragments(root: Path, version: str, changelog: str = CHANGELOG, fragments_dir: str = FRAGMENTS_DIR) -> int:
    """Fold the fragments into the changelog and delete them; how many were folded."""
    text, files = pending(root, version, changelog, fragments_dir)
    if files:
        (Path(root) / changelog).write_text(text, "utf-8", newline="\n")
        for f in files:
            f.unlink()
    return len(files)


def notes_section(changelog: str, version: str) -> str:
    """The body of the changelog's `### <version> (<date>)` section."""
    m = re.search(rf"^### {re.escape(version)} \(.*?\)[ \t]*\n(.*?)(?=^### |\Z)", changelog, re.M | re.S)
    if not m:
        raise ChangelogError(f"{CHANGELOG} has no '### {version} (<date>)' section")
    return m.group(1).strip()


def main(argv: list[str] | None = None) -> int:
    """`py -3 release/changelog.py fold --root . --version 1.2.3`: fold the fragments into the changelog and delete them."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("command", choices=["fold"])
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="the mod project folder (default: the current folder)")
    ap.add_argument("--version", required=True, help="release version (the section the fragments fold into)")
    ap.add_argument("--changelog", default=CHANGELOG)
    ap.add_argument("--fragments", default=FRAGMENTS_DIR)
    a = ap.parse_args(argv)
    try:
        n = fold_fragments(a.root, a.version.lstrip("v"), a.changelog, a.fragments)
    except ChangelogError as e:
        print(f"changelog: {e}", file=sys.stderr)
        return 1
    print(f"changelog: folded {n} fragments from {a.fragments}/")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
