"""The merge driver of a classic import: rebuild a project's generated/ from its committed rule files.

Each file in the rules folder is applied by the rule kind its name maps to in the project's `rules` (`*.md` files are
notes); a file with no rule kind fails the run, so a rule is never silently skipped. Rules run in file-name order. A
rule is fn(rule file, extracted data root, D2R data root, generated/data). Every run rebuilds generated/ from scratch,
and a failed run leaves no generated/, so a build never picks up half a merge.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from . import extract

Rule = Callable[[Path, Path, Path, Path], None]


class MergeError(Exception):
    pass


def check_extract(extracted: Path, baseline_file: Path) -> None:
    """Refuse an extract that is missing, unfinished, or from another baseline file than the project's."""
    done = extracted / "baseline.json"
    if not done.is_file():
        raise MergeError(f"{extracted} has no baseline stamp: run the extract")
    if done.read_bytes() != extract.stamp(baseline_file.read_bytes()):
        raise MergeError(f"{extracted} was extracted from another baseline or by an older extract: run the extract "
                         "again")


def merge(rules: dict[str, Rule], rules_dir: Path, data: Path, d2r: Path, generated: Path,
          errors: tuple[type[BaseException], ...] = ()) -> list[str]:
    """Rebuild generated/ (the rules write generated/data) and return the rule files applied. A ValueError from a rule
    is a data error named by its rule file; `errors` are the project's own error types, reported as MergeError too."""
    files = sorted(p for p in rules_dir.glob("*") if p.is_file() and p.suffix != ".md") if rules_dir.exists() else []
    unknown = [p.name for p in files if p.name not in rules]
    if unknown:
        raise MergeError(f"{rules_dir.name}/ files with no rule kind: {', '.join(unknown)}")
    if files and not (d2r / "global" / "excel").is_dir():
        raise MergeError(f"no D2R tables under {d2r}: run `modkit fetch` or pass the D2R data root")
    out = generated / "data"
    if generated.exists():
        shutil.rmtree(generated)
    out.mkdir(parents=True)
    try:
        for p in files:
            try:
                rules[p.name](p, data, d2r, out)
            except ValueError as e:  # a rule's data error, named by its rule file
                raise MergeError(f"{rules_dir.name}/{p.name}: {e}") from e
    except (MergeError, *errors) as e:
        shutil.rmtree(generated)
        raise MergeError(str(e)) from e
    except BaseException:
        shutil.rmtree(generated)
        raise
    return [p.name for p in files]
