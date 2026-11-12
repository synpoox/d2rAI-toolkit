"""Extract a classic install's files into a folder, after checking the install against its baseline file.

The baseline file (JSON) names the install and pins it:

    {"install": "<folder>",
     "archives": {"<name>.mpq": "<sha256>", ...},         every archive must match, or nothing is extracted
     "dlls": {"<name>.dll": "<sha256>", ...},             optional: a mismatch only warns
     "extract": {"<name>.mpq": ["<pattern>", ...], ...}}  the files to take: lower-case paths, fnmatch patterns

Files land in out/ as lower-case paths with forward slashes (out/data/global/excel/skills.txt). out/baseline.json, a
copy of the baseline file written last, marks a finished extract: a run with the same baseline file skips the work, and
merge.check_extract refuses an out/ extracted from any other one. A change to the patterns is a change to the file, so
an extract never silently lacks files the patterns have since added.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
import sys
from pathlib import Path

from . import cache, mpq


def stamp(baseline: bytes) -> bytes:
    """out/baseline.json's bytes for this baseline file."""
    return baseline


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(install: Path, baseline: dict, name: str = "the baseline") -> list[str]:
    """Problems with the install or the baseline, empty when every archive matches. DLLs only warn."""
    problems = []
    for archive, want in baseline["archives"].items():
        p = install / archive
        if not p.is_file():
            problems.append(f"{archive}: missing from {install}")
        elif sha256(p) != want:
            problems.append(f"{archive}: SHA-256 differs from {name}")
    for dll, want in baseline.get("dlls", {}).items():
        p = install / dll
        if p.is_file() and sha256(p) != want:
            print(f"warning: {dll} differs from {name} (reference only)")
    if "extract" not in baseline:
        problems.append(f"{name} has no \"extract\" key: name the files to take from each archive")
    for archive in baseline.get("extract", {}):
        if archive not in baseline["archives"]:
            problems.append(f"extract names {archive}, which {name}'s archives does not pin")
    return problems


def extract(install: Path, out: Path, baseline_file: Path) -> int:
    """Extract into out (0), or refuse an install that is not the baseline (1, nothing written)."""
    raw = baseline_file.read_bytes()
    baseline = json.loads(raw)
    problems = check(install, baseline, baseline_file.name)
    if problems:
        print(f"refusing: this install is not {baseline_file.name}'s\n  " + "\n  ".join(problems)
              + f"\nRe-baselining is a deliberate commit to {baseline_file.name}.", file=sys.stderr)
        return 1
    done = out / "baseline.json"  # written last, so it only exists after a finished extract
    if done.is_file() and done.read_bytes() == stamp(raw):
        print(f"{out} is current, skipping extract")
        return 0
    if out.exists():
        shutil.rmtree(out)
    count = 0
    for archive, patterns in baseline["extract"].items():
        a = mpq.Archive(install / archive)
        for name in a.names():
            rel = name.replace("\\", "/").lower()
            if not any(fnmatch.fnmatchcase(rel, p) for p in patterns):
                continue
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(a.read(name))
            count += 1
    done.parent.mkdir(parents=True, exist_ok=True)
    done.write_bytes(stamp(raw))
    print(f"extracted {count} files to {out}")
    return 0


def extract_shared(install: Path, out: Path, baseline_file: Path, cache_root: Path | None = None,
                   own_folder: bool = False) -> int:
    """`extract`, under a lock, and shared between worktrees: with a cache root (and unless own_folder: the caller named
    out itself) out becomes a junction or symlink to the cache's extract for this baseline file, `<root>/extract/<stamp>`,
    so every worktree reads one extract. An out that is already a real folder is kept as it is. Runs never overlap: they
    hold `extract.lock` under the cache root (else beside out). Returns extract's code."""
    with cache.lock((cache_root or out.parent) / "extract.lock"):
        if own_folder or not cache_root or (out.exists() and not cache.is_link(out)):
            if not own_folder and cache_root:
                print(f"{out} is a folder, not the shared extract: delete it to use {cache_root / 'extract'}")
            return extract(install, out, baseline_file)
        shared = cache_root / "extract" / hashlib.sha256(stamp(baseline_file.read_bytes())).hexdigest()[:16]
        rc = extract(install, shared, baseline_file)
        if rc == 0:
            cache.point(out, shared)
            print(f"{out} -> {shared}")
        return rc
