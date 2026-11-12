"""The merge driver of a classic import: rebuild a project's generated/ from its committed rule files.

Each file in the rules folder is applied by the rule kind its name maps to in the project's `rules` (`*.md` files are
notes); a file with no rule kind fails the run, so a rule is never silently skipped. Rules run in file-name order. A
rule is fn(rule file, extracted data root, D2R data root, generated/data). Every run rebuilds generated/ from scratch,
and a failed run leaves no generated/, so a build never picks up half a merge.

`run` wraps `merge` for a project that wants the machine-wide rule cache (cache.py, opt in with MODKIT_SHARED_CACHE):
one run per project folder at a time (a lock), each rule replayed from the cache when its code, the stamps and the files
it read are unchanged, a merge slot taken at the first rule that must run, the output checked before it is handed back
and, when it is not whole, rebuilt once with no rule cache before the run fails. The project passes its rules map in.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable

from . import cache, extract

KIT = Path(__file__).resolve().parents[2]  # the toolkit's own folder: the cache keys the toolkit modules a rule imports

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


def check_output(gen: Path, required: tuple[str, ...] = (), minimum: int = 0) -> str | None:
    """Why gen (generated/data) is not a whole merge, or None when it is: `required` tables must be in global/excel and
    it must hold at least `minimum` tables. A partial tree is what a racing or killed run leaves, so a project passes
    its own table set (with the defaults every tree passes)."""
    excel = gen / "global" / "excel"
    have = {p.name for p in excel.glob("*.txt")} if excel.is_dir() else set()
    missing = [t for t in required if t not in have]
    if missing:
        return f"{excel} lacks {', '.join(missing)}"
    if len(have) < minimum:
        return f"{excel} holds {len(have)} tables, fewer than {minimum}"
    return None


def base_key(stamps: list[Path], kit: Path, d2r: Path) -> str:
    """Every rule's key base: the stamp files (the project's baseline file and the extract's stamp), the toolkit's merge
    driver (this module and what it imports), D2R's path and the cache's format (cache.CACHE_FORMAT, not cache.py's
    bytes: an edit to the cache's code must not rebuild every rule). The toolkit modules a rule itself imports are in
    its own key (rule_key)."""
    driver = cache.toolkit_sources(kit, [kit / "shared" / "classic_import" / "merge.py"])
    return cache.key([*stamps, *driver], str(d2r.resolve()), str(cache.CACHE_FORMAT))


def rule_key(fn: Callable, kit: Path, base: str, name: str) -> str:
    """One rule's key: its own code, the toolkit modules that code imports, and the base."""
    srcs = cache.sources(fn)
    return cache.key(srcs + cache.toolkit_sources(kit, srcs), base, name, fn.__qualname__)


def cache_setup() -> tuple[Path | None, cache.Policy]:
    """The cache root and policy of this process from the environment: the opt-in root (MODKIT_SHARED_CACHE) with the
    default policy; on CI the shared root under the CI scope policy (MODKIT_CI_SCOPE); else (None, default)."""
    root, policy = cache.root(), cache.Policy()
    if os.environ.get("GITHUB_ACTIONS") and (home := cache.slot_home()) and (ci := cache.ci_policy(home)):
        root, policy = home, ci
    return root, policy


def prune_cache(root: Path) -> list[Path]:
    """Prune the rule cache to MODKIT_CACHE_GB (default 20) and return the entries deleted."""
    return cache.prune(root, cache.cap_bytes())


def run(rules: dict[str, Rule], rules_dir: Path, data: Path, d2r: Path, generated: Path, baseline_file: Path,
        extracted: Path, errors: tuple[type[BaseException], ...] = (), rule_cache: Path | None = None,
        slots_home: Path | None = None, policy: cache.Policy = cache.Policy(), kit: Path = KIT,
        required: tuple[str, ...] = (), minimum: int = 0) -> list[str]:
    """`merge`, with the rule cache and the machine-wide merge cap, and return the rule files applied.

    rule_cache: the folder the rule entries live in (`<cache root>/rules`), or None for no cache. slots_home: the cache
    root the merge slot is taken under (also set on CI, which has no rule cache but shares the machine). policy: whose
    entries may be replayed and where a miss is kept. required, minimum: see check_output. A second run in the same
    project waits for the first, so a rebuild of generated/ never shows up in the other run's rule snapshots."""
    project = generated.parent
    home = rule_cache.parent if rule_cache else slots_home
    slots = cache.merge_slots(home) if home else None
    ran: list[str] = []
    used_rules = rules
    if rule_cache:
        base = base_key([baseline_file, extracted / "baseline.json"], kit, d2r)

        def cached(name: str, fn: Rule) -> Rule:
            def go(p: Path, d: Path, d2r_: Path, out: Path) -> None:
                def work() -> None:
                    slots.acquire()
                    fn(p, d, d2r_, out)
                if not cache.rule(rule_cache, rule_key(fn, kit, base, name), {"p": project, "d": d2r_}, work, policy,
                                  slots):
                    ran.append(name)
            return go
        used_rules = {n: cached(n, fn) for n, fn in rules.items()}

    def apply(rules_: dict[str, Rule]) -> list[str]:
        if slots and rules_ is rules:
            slots.acquire()  # the uncached rebuild runs every rule
        check_extract(extracted, baseline_file)
        return merge(rules_, rules_dir, data, d2r, generated, errors)

    rebuilt = False
    try:
        with cache.lock(project / "merge.lock"):
            cache.used.clear()
            applied = apply(used_rules)
            if (why := check_output(generated / "data", required, minimum)) is not None:
                # a partial entry would be replayed, and fail, on every later run; only the tables are checked
                cache.evict(cache.own(cache.used, policy), "data/global/excel/")
                print(f"merge output is not whole ({why}): rebuilding without the rule cache", flush=True)
                applied, rebuilt = apply(rules), True
                if (why := check_output(generated / "data", required, minimum)) is not None:
                    raise MergeError(f"merge output is not whole after a rebuild: {why}")
    finally:
        if slots:
            slots.release()
    if rule_cache and not rebuilt:
        print(f"rule cache: {len(applied) - len(ran)} of {len(applied)} rules replayed; ran {', '.join(ran) or 'none'}")
    return applied
