"""HD looks of the rows a classic port adds: missiles, monsters, objects and overlays. D2R's HD renderer draws a row
only when its own JSON lists it, so a row the port appends without an entry works but draws nothing. Each section's
rule file has one `name <tab> like` line per row whose art D2R lacks (the source's own art): the D2R row whose model it
takes as a stand-in. A new row with no model fails the merge, so none is skipped silently; so does a line for a row
that is not new, so the list never goes stale.

    apply_missiles   data/hd/missiles/missiles.json   rule: missile <tab> like. A new missile takes the model of the D2R
                     missile with the same `CelFile` (the classic art; the model most D2R rows with it use).
    apply_monsters   data/hd/character/monsters.json  rule: monster <tab> like. A new monster takes the model of its
                     `BaseId` when that is a D2R monster with the same `Code` (a clone names its original there), else
                     the model most D2R rows with its `Code` use. A line is needed for source-only art, a tie, or a wrong
                     pick; one that picks the model the monster gets anyway is stale. D2R reads the keys case
                     sensitively: a key is the exact monstats `Id`.
    apply_objects    data/hd/objects/objects.json     rule: class <tab> like [<tab> particles]. D2R draws an object from
                     objects.json (key: the objects.txt `Class` in snake case, value: its folder) and
                     <folder>/<key>.json; the line names the D2R key whose json it copies, and optionally a .particles
                     path replacing the like's one particle effect (its colour).
    apply_overlays   data/hd/overlays/<Character>/<overlay>.json  rule: overlay <tab> like. The new row takes the
                     like's folder (overlay.txt `Character`); the copy's name keeps the source's spelling with D2R's `_`
                     between a letter and a digit. Run after the table merge that writes overlay.txt.

Each apply reads the rule file, D2R's data and the table the merge wrote, and is a rule kind for the merge driver.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .ids import Table, excel

HD_MISSILES = Path("hd") / "missiles" / "missiles.json"
HD_MONSTERS = Path("hd") / "character" / "monsters.json"
HD_OBJECTS = Path("hd") / "objects"
HD_OVERLAYS = Path("hd") / "overlays"


class HdError(ValueError):
    pass


class MissileHdError(HdError):
    pass


class MonsterHdError(HdError):
    pass


class ObjectHdError(HdError):
    pass


class OverlayHdError(HdError):
    pass


def read_likes(path: Path, error: type[HdError], what: str, lower: bool = True) -> dict[str, str]:
    """A rule file of `what<tab>like` lines (# comments): {what (lower case unless lower is False): like}."""
    likes = {}
    for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        if line and not line.startswith("#"):
            parts = line.split("\t")
            if len(parts) != 2 or not all(parts):
                raise error(f"line {n}: want '{what}<tab>like'")
            likes[parts[0].lower() if lower else parts[0]] = parts[1]
    return likes


# --- missiles ---

def missile_key(name: str, lower: bool = True) -> str:
    """D2R's spelling of a missile name in missiles.json: bighead1 -> bighead_1, bomb in air -> bomb_in_air."""
    return re.sub(r"([A-Za-z])(\d)", r"\1_\2", (name.lower() if lower else name).replace(" ", "_"))


def cel(row: list[str], col: int) -> str:
    return row[col].lower().rsplit("\\", 1)[-1]  # the games differ on the expansion\ folder prefix


def missile_entries(mod: Table, d2r: Table, models: dict, likes: dict[str, str]) -> dict[str, str]:
    """missiles.json key -> model for every mod row not in D2R's table. likes: missile (lower case) -> D2R missile."""
    c, dc = mod.header.index("CelFile"), d2r.header.index("CelFile")
    by_cel: dict[str, Counter] = {}
    for r in d2r.rows:
        if r[0] and missile_key(r[0]) in models:
            by_cel.setdefault(cel(r, dc), Counter())[models[missile_key(r[0])]] += 1
    vanilla = {r[0].lower() for r in d2r.rows}
    out, missing, stale = {}, [], set(likes)
    for r in mod.rows:
        name = r[0]
        if not name or name.lower() in vanilla:
            continue
        key, like = missile_key(name), likes.get(name.lower())
        # JSON keys are case-sensitive, and no vanilla missile name has a capital, so it is unproven whether D2R
        # lower-cases one before the lookup: a name with capitals gets its model under both spellings
        own = missile_key(name, lower=False)
        stale.discard(name.lower())
        for k in {key, own}:
            if k in models or k in out:
                raise MissileHdError(f"'{name}': missiles.json already has '{k}'")
        if like is not None:
            if cel(r, c) in by_cel:
                raise MissileHdError(f"'{name}' has a CelFile match ({by_cel[cel(r, c)].most_common(1)[0][0]}): "
                                     "delete its line")
            if missile_key(like) not in models:
                raise MissileHdError(f"'{name}': '{like}' has no missiles.json entry")
            out[key] = models[missile_key(like)]
        elif cel(r, c) in by_cel:
            out[key] = by_cel[cel(r, c)].most_common(1)[0][0]
        else:
            missing.append(f"{name} ({r[c] or 'no CelFile'})")
            continue
        out[own] = out[key]
    if missing:
        raise MissileHdError(f"no HD model for {len(missing)} new missiles, add lines: {', '.join(missing)}")
    if stale:
        raise MissileHdError(f"lines for missiles that are not new: {', '.join(sorted(stale))}")
    return out


def classic_sprites(mod: Table, src_data: Path, out_data: Path) -> int:
    """Copy the source's DCC for every row whose CelFile src_data has: D2R ships none of a classic mod's own missile art,
    so legacy mode would draw nothing for those missiles. Returns the count."""
    c, src, dst = mod.header.index("CelFile"), src_data / "global" / "missiles", out_data / "global" / "missiles"
    names = sorted({f"{cel(r, c)}.dcc" for r in mod.rows if r[c] and (src / f"{cel(r, c)}.dcc").is_file()})
    dst.mkdir(parents=True, exist_ok=True)
    for n in names:
        (dst / n).write_bytes((src / n).read_bytes())
    return len(names)


def apply_missiles(rule: Path, src_data: Path, d2r_data: Path, out_data: Path) -> None:
    """Rule kind for the missiles HD rule file: write missiles.json for the missiles.txt the id rule wrote (run
    after the id rule for missiles)."""
    models = json.loads((d2r_data / HD_MISSILES).read_text("utf-8-sig"))
    new = missile_entries(Table(excel(out_data) / "missiles.txt"), Table(excel(d2r_data) / "missiles.txt"), models,
                          read_likes(rule, MissileHdError, "missile"))
    (out_data / HD_MISSILES).parent.mkdir(parents=True, exist_ok=True)
    (out_data / HD_MISSILES).write_text(json.dumps(models | new, separators=(",", ":")), "utf-8")
    sprites = classic_sprites(Table(excel(out_data) / "missiles.txt"), src_data, out_data)
    print(f"  missiles-hd: {len(new)} entries for new missiles, {sprites} classic sprites")


# --- monsters ---

def monster_entries(src: Table, d2r: Table, models: dict, likes: dict[str, str]) -> dict[str, str]:
    """monsters.json key -> model for every source row not in D2R's table. likes: monster (lower case) -> D2R monster."""
    code_col, base_col, dc = src.header.index("Code"), src.header.index("BaseId"), d2r.header.index("Code")
    by_code: dict[str, Counter] = {}
    code_of = {}
    for r in d2r.rows:
        code_of[r[0].lower()] = r[dc].lower()
        if r[0].lower() in models:
            by_code.setdefault(r[dc].lower(), Counter())[models[r[0].lower()]] += 1
    out, missing, stale = {}, [], set(likes)
    for r in src.rows:
        name = r[0]  # D2R looks keys up case-sensitively, so the key is the exact Id
        low = name.lower()
        if not name or low in code_of:
            continue
        like, code, base = likes.get(low), r[code_col].lower(), r[base_col].lower()
        stale.discard(low)
        if name in models or name in out:
            raise MonsterHdError(f"'{name}': monsters.json already has '{name}'")
        top = by_code[code].most_common(2) if code in by_code else []
        if base in models and code_of.get(base) == code:
            auto = models[base]  # the model it gets with no line
        elif len(top) == 1 or top and top[0][1] > top[1][1]:
            auto = top[0][0]
        else:  # no model, or a tie that only D2R's row order would break
            auto = None
        if like is not None:
            if like.lower() not in models:
                raise MonsterHdError(f"'{name}': '{like}' has no monsters.json entry")
            if models[like.lower()] == auto:
                raise MonsterHdError(f"'{name}' gets {auto} anyway: delete its line")
            out[name] = models[like.lower()]
        elif auto is not None:
            out[name] = auto
        else:
            tie = f", tie: {' or '.join(m for m, _ in top)}" if top else ""
            missing.append(f"{name} ({r[code_col] or 'no Code'}{tie})")
    if missing:
        raise MonsterHdError(f"no HD model for {len(missing)} new monsters, add lines: {', '.join(missing)}")
    if stale:
        raise MonsterHdError(f"lines for monsters that are not new: {', '.join(sorted(stale))}")
    return out


def apply_monsters(rule: Path, src_data: Path, d2r_data: Path, out_data: Path) -> None:
    """Rule kind for the monsters HD rule file: write monsters.json. Reads the source's monstats, not the merged one
    (the table merge keeps every Id), so the rule needs no place in the run order."""
    models = json.loads((d2r_data / HD_MONSTERS).read_text("utf-8-sig"))
    new = monster_entries(Table(excel(src_data) / "monstats.txt"), Table(excel(d2r_data) / "monstats.txt"), models,
                          read_likes(rule, MonsterHdError, "monster"))
    (out_data / HD_MONSTERS).parent.mkdir(parents=True, exist_ok=True)
    (out_data / HD_MONSTERS).write_text(json.dumps(models | new, separators=(",", ":")), "utf-8")
    print(f"  monsters-hd: {len(new)} new monsters mapped")


# --- objects ---

def object_key(cls: str) -> str:
    """D2R's objects.json key of an objects.txt Class: `_` between words and between letters and digits, lower case
    (`ConsolationChest` is `consolation_chest`, `Chest1B` is `chest_1_b`)."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])|(?<=[A-Z])(?=[A-Z][a-z])", "_",
                  cls).lower()


def read_object_lines(path: Path) -> dict[str, tuple[str, str]]:
    """class -> (like, particles path or "")."""
    likes = {}
    for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        if line and not line.startswith("#"):
            parts = line.split("\t")
            if len(parts) not in (2, 3) or not all(parts):
                raise ObjectHdError(f"line {n}: want 'class<tab>like[<tab>particles]'")
            likes[parts[0]] = (parts[1], parts[2] if len(parts) == 3 else "")
    return likes


def apply_objects(rule: Path, src_data: Path, d2r_data: Path, out_data: Path) -> None:
    """Rule kind for the objects HD rule file: objects.json plus a stand-in json per listed class (run after the id rule
    for objects). A line for a class that is not a source-only objects row, or a like D2R lacks, fails the merge."""
    likes = read_object_lines(rule)
    folders = json.loads((d2r_data / HD_OBJECTS / "objects.json").read_text("utf-8-sig"))
    d2r = {r[0] for r in Table(excel(d2r_data) / "objects.txt").rows}
    new = {r[0] for r in Table(excel(out_data) / "objects.txt").rows} - d2r
    for cls, (like, particles) in likes.items():
        if cls not in new:
            raise ObjectHdError(f"'{cls}' is not a source-only objects Class")
        src = d2r_data / HD_OBJECTS / folders.get(like, {}).get("asset_path", "") / f"{like}.json"
        if like not in folders or not src.is_file():
            raise ObjectHdError(f"'{cls}': '{like}' has no D2R object json")
        folder = folders[like]["asset_path"]
        (out_data / HD_OBJECTS / folder).mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        if particles:
            old = [d["path"] for d in json.loads(data)["dependencies"]["particles"]]
            if len(old) != 1:
                raise ObjectHdError(f"'{cls}': '{like}' has {len(old)} particle effects, want 1 to replace")
            data = data.replace(old[0].encode(), particles.encode())
        (out_data / HD_OBJECTS / folder / f"{object_key(cls)}.json").write_bytes(data)
        folders[object_key(cls)] = {"asset_path": folder}
    (out_data / HD_OBJECTS / "objects.json").write_text(json.dumps(folders, indent=1), "utf-8")
    print(f"  objects-hd: {len(likes)} new objects drawn")


# --- overlays ---

def apply_overlays(rule: Path, src_data: Path, d2r_data: Path, out_data: Path) -> None:
    """Rule kind for the overlays HD rule file: the new rows' `Character` and their stand-in jsons. The table merge
    keeps D2R's `Character` on shared rows (a classic table's are classic values) and leaves appended rows blank, which
    this fills; run it after that merge."""
    likes = read_likes(rule, OverlayHdError, "overlay")
    d2r = Table(excel(d2r_data) / "overlay.txt")
    merged_path = excel(out_data) / "overlay.txt"
    merged = Table(merged_path)
    ch = merged.header.index("Character")
    folder = {r[0].lower(): r[d2r.header.index("Character")] for r in d2r.rows}
    missing, stale = [], set(likes)
    for r in merged.rows:
        name = r[0]
        if not name or name.lower() in folder:
            continue
        stale.discard(name.lower())
        like = likes.get(name.lower())
        if like is None:
            missing.append(name)
            continue
        src = d2r_data / HD_OVERLAYS / folder.get(like.lower(), "") / f"{like.lower()}.json"
        if like.lower() not in folder or not src.is_file():
            raise OverlayHdError(f"'{name}': '{like}' has no D2R overlay json")
        r[ch] = folder[like.lower()]
        file = re.sub(r"([A-Za-z])(\d)", r"\1_\2", name)  # D2R's own doubledamage1 is doubledamage_1.json
        copy = json.loads(src.read_text("utf-8-sig")) | {"name": file}
        dest = out_data / HD_OVERLAYS / r[ch] / f"{file}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(copy, separators=(",", ":")), "utf-8")
    if missing:
        raise OverlayHdError(f"no HD overlay for {len(missing)} new overlays, add lines: {', '.join(missing)}")
    if stale:
        raise OverlayHdError(f"lines for overlays that are not new: {', '.join(sorted(stale))}")
    merged_path.write_bytes(merged.text().encode("latin-1"))
    print(f"  vfx-overlays: {len(likes)} new overlays given a D2R stand-in")
