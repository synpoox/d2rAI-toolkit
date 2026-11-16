"""Item tables with no id list: merged by key around D2R's rows, the cube, items kept from dropping, and the HD
inventory pictures new items need. The rule file (a project's merge/item-tables.txt) is:

    merge <tab> <table>                 merge the source's table onto D2R's by key (ids.KEY, the project's vanilla counts)
    no-drop <tab> <type or code> ...    items of this type (or its descendants) or code never drop

A source row takes the D2R row with the same key; D2R-only rows stay where D2R has them and source-only rows are
appended, as ids does for the id-listed tables. The cube keeps the source's recipes in the source's order, then D2R's
recipes the source has no recipe with the same inputs and outputs for. What a project's own engine does to its recipes
(a rule for a recipe op, an output D2R spells differently) comes in as `fixes`: functions of the merged cube table.

The source's own item pictures (an invfile no D2R item uses) are upscaled into HD sprites (the project passes its
upscaler in) and drawn by every item, unique and set item that names them; the others borrow a D2R picture (hd_items).

A never-dropping item leaves every treasure class: its weight goes to NoDrop, so every other item drops at the source's
rate (exact for one player; NoDrop shrinks with more players), and a counted (negative Picks) entry is removed. A
treasure class holding only such items counts as one. Its items row is made unspawnable too.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Sequence

from modkit import dc6, hd, images

from . import ids as I

ITEM_TABLES = ["weapons", "armor", "misc"]
CUBE_FIX = Callable[["I.Table"], None]  # a fix to the merged cube table, in place
# a recipe's signature: the inputs and outputs. A D2R recipe with the same one as a source recipe is replaced by it
SIGNATURE = [*(f"input {k}" for k in range(1, 8)), "output", "output b", "output c"]
HD_PER_CLASSIC = 3.5  # D2R's 98 px inventory cell over the classic 28 px


def read_rule(path: Path, vanilla: dict[str, int]) -> tuple[list[str], set[str]]:
    """The tables to merge and the never-dropping types or codes of a rule file. `vanilla` names the tables a project
    merges by key (a table needs a vanilla row count there); cubemain needs none."""
    tables, no_drop = [], set()  # a no-drop line may list several types or codes; a merge line takes exactly one table
    for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        parts = line.split("\t")
        if not line or line.startswith("#"):
            continue
        if len(parts) < 2 or parts[0] not in ("merge", "no-drop"):
            raise I.IdError(f"{path.name} line {n}: want 'merge<tab>table' or 'no-drop<tab>type or code'")
        if parts[0] == "merge" and parts[1] not in vanilla and parts[1] != "cubemain":
            raise I.IdError(f"{path.name} line {n}: no merge rule for table '{parts[1]}'")
        if parts[0] == "merge":
            if len(parts) != 2:
                raise I.IdError(f"{path.name} line {n}: 'merge' takes one table, got {len(parts) - 1} fields "
                                f"(unexpected: {', '.join(parts[2:])})")
            tables.append(parts[1])
        else:
            no_drop.update(p for p in parts[1:] if p)
    return tables, no_drop


def _finish(table: str, ctx: I.Context, finish: I.Finish | None) -> I.Finish | None:
    """The property fixes for a table of item properties, then the project's own finish."""
    return I.finishes(I.props_finish(ctx.ren, ctx.ids, ctx.props) if table in I.PROPS else None, finish)


def merge_keyed(table: str, src: I.Table, d2r: I.Table, ctx: I.Context, vanilla: dict[str, int], suffix: str, *,
                by_source_order: set[str] = frozenset(), finish: I.Finish | None = None,
                fix_row: I.FixRow | None = None, spell: I.Spell = I.spell, source: str = "the source's"
                ) -> I.Table:
    """The table merged by key around D2R's rows (`vanilla`: rows below the project's vanilla count keep their ids;
    `suffix` names a clashing source row). A table in by_source_order is named, never numbered, and a row must come
    after the rows it names (treasure classes): the source's rows in the source's order, then D2R-only ones. The
    merged table's `dropped` is the source columns D2R has no place for."""
    lines = I.seed(table, src.names(), d2r.names(), [], vanilla.get(table, 0), suffix)
    merged, dropped = I.merge_table(table, src, d2r, lines, ctx.ren, ctx.ids, spell=spell, fix_row=fix_row,
                                    finish=_finish(table, ctx, finish), source=source)
    merged.dropped = dropped
    if table in by_source_order:
        rank = {n: k for k, (_, _, n) in enumerate(lines)}
        merged.rows.sort(key=lambda r: rank.get(r[merged.key], len(rank)))  # stable: D2R-only rows keep D2R's order
    return merged


def merge_cube(src: I.Table, d2r: I.Table, ctx: I.Context, fixes: Sequence[CUBE_FIX] = (),
               after: Sequence[CUBE_FIX] = (), finish: I.Finish | None = None, source: str = "the source's"
               ) -> I.Table:
    """cubemain: the source's recipes in the source's order, then D2R's recipes no source recipe has the same inputs
    and outputs as. `fixes` change the merged source recipes (before D2R's are added), `after` the whole table. The
    merged table's `dropped` is the source columns D2R has no place for."""
    def signature(t: I.Table, row: list[str]) -> tuple[str, ...]:
        return tuple(row[t.header.index(c)].replace('"', "").lower() if c in t.header else "" for c in SIGNATURE)
    src_sigs = {signature(src, r) for r in src.rows}
    d2r_only = [r for r in d2r.rows if signature(d2r, r) not in src_sigs]
    empty = I.Table.of(d2r.header, [], d2r.newline, 0)
    lines = [(p, k, I.base(p).replace('"', "")) for k, p in enumerate(I.ident(src.names()))]
    merged, dropped = I.merge_table("cubemain", src, empty, lines, ctx.ren, ctx.ids,
                                    finish=_finish("cubemain", ctx, finish), source=source)
    for fix in fixes:
        fix(merged)
    merged.rows += [list(r) for r in d2r_only]
    for fix in after:
        fix(merged)
    merged.dropped = dropped
    return merged


def count_each_input(cube: I.Table, skip_ops: tuple[str, ...] = ()) -> None:
    """A classic engine's numinputs may count stacks ("t1me,qty=3" is 1); D2R's recipe search wants numinputs == items
    in the cube, so loose inputs matched no row. Each row gets the sum of its inputs' qty. Rows with an op in skip_ops
    (matched without the count) keep theirs. Use it as a `fixes` entry when the source engine counted stacks."""
    h = {c: j for j, c in enumerate(cube.header)}
    if "numinputs" not in h:
        return
    inputs = [h[c] for c in (f"input {k}" for k in range(1, 8)) if c in h]
    for r in cube.rows:
        if not r[h["numinputs"]].strip() or ("op" in h and r[h["op"]] in skip_ops):
            continue
        r[h["numinputs"]] = str(sum(int(m[1]) if (m := re.search(r"qty=(\d+)", r[i])) else 1
                                    for i in inputs if r[i].strip('"')))


def block_drops(tc: I.Table, items: dict[str, I.Table], itemtypes: I.Table, no_drop: set[str]) -> set[str]:
    """Take the no_drop items out of every treasure class (module docstring). Returns the item codes blocked."""
    h = {c: j for j, c in enumerate(itemtypes.header)}
    parents = {r[itemtypes.key]: [r[h[c]] for c in ("Equiv1", "Equiv2") if c in h and r[h[c]]] for r in itemtypes.rows}

    def blocked_type(t: str, seen: frozenset = frozenset()) -> bool:
        return t in no_drop or any(blocked_type(p, seen | {t}) for p in parents.get(t, []) if p not in seen)
    codes = set()
    for t in items.values():
        ty, sp = t.header.index("type"), t.header.index("spawnable")
        for r in t.rows:
            if r[t.key] and (r[t.key] in no_drop or blocked_type(r[ty])):
                codes.add(r[t.key])
                r[sp] = "0"
    th = {c: j for j, c in enumerate(tc.header)}
    slots = [(th[f"Item{k}"], th[f"Prob{k}"]) for k in range(1, 11) if f"Item{k}" in th]
    gone = set(codes)
    while True:  # treasure classes holding only blocked entries count as blocked
        more = {r[tc.key] for r in tc.rows if r[tc.key] not in gone and (es := [r[i] for i, _ in slots if r[i]])
                and all(e in gone for e in es)}
        if not more:
            break
        gone |= more
    for r in tc.rows:
        kept = [(r[i], r[p]) for i, p in slots if r[i] and r[i] not in gone]
        lost = [r[p] for i, p in slots if r[i] and r[i] in gone]
        if not lost:
            continue
        picks = int(r[th["Picks"]] or 0)
        if picks < 0:  # counted picks: each entry's Prob is how many of it drop
            r[th["Picks"]] = str(picks + sum(int(v or 0) for v in lost))
        else:
            r[th["NoDrop"]] = str(int(r[th["NoDrop"]] or 0) + sum(int(v or 0) for v in lost))
        for k, (i, p) in enumerate(slots):
            r[i], r[p] = kept[k] if k < len(kept) else ("", "")
    return codes


def _entries(path: Path) -> list[dict]:
    return json.loads(path.read_text("utf-8-sig"))


def item_pictures(upscale: Callable[[Path, dict], dict], art: Path, src_data: Path, d2r_data: Path, out_data: Path,
                  uses: dict[str, set[str]], d2r_inv: set[str]) -> dict[str, str]:
    """The source's own pictures, an invfile in uses (-> the item tables drawing it) that no D2R item uses and src_data
    has a DC6 for: an HD sprite upscaled from it in each table's folder, and the DC6 for legacy mode. `upscale(art,
    {name: classic frame})` returns {name: bigger image} (the project's upscaler and its art cache). Returns
    {invfile: items.json asset}."""
    classic = Path("global") / "items"
    if not (src_data / classic).is_dir():  # else every source picture is silently dropped
        raise I.IdError(f"{src_data / classic}: no item pictures; run the extract again")
    names = sorted(n for n in uses if n not in d2r_inv and (src_data / classic / f"{n}.dc6").is_file())
    pal = dc6.palette((d2r_data / "global" / "palette" / "units" / "pal.dat").read_bytes())
    frames = {n: dc6.decode(dc6.read(src_data / classic / f"{n}.dc6")[0], pal) for n in names}
    big = upscale(art, {f"items/{n}": f for n, f in frames.items()})
    (out_data / classic).mkdir(parents=True, exist_ok=True)
    for n in names:
        w, h, _ = frames[n]
        sprite = images.scale(big[f"items/{n}"], round(w * HD_PER_CLASSIC), round(h * HD_PER_CLASSIC))
        for t in sorted(uses[n]):
            images.write_sprite(out_data / "hd" / "global" / "ui" / "items" / hd.item_folder(t) / "src" / f"{n}.sprite",
                                sprite)
        (out_data / classic / f"{n}.dc6").write_bytes((src_data / classic / f"{n}.dc6").read_bytes())
    return {n: f"src/{n}" for n in names}


def hd_items(hd_dir: Path, src: dict[str, I.Table], d2r: dict[str, I.Table],
             uniques: list[tuple[str, str, str | None, str]], sets: list[tuple[str, str, str | None, str]],
             pictures: dict[str, str] | None = None, models: dict[str, str] | None = None,
             borrowed: dict[tuple[str, str], str] | None = None,
             neutral_model: dict[str, str] | None = None) -> dict[str, list[dict]]:
    """D2R's items.json, uniques.json and sets.json (from hd_dir) plus an entry for every item code, unique and set item
    that has none. An item whose invfile is in pictures (item_pictures) shows it; else a new code shows the picture
    of the D2R item in the same table with the same invfile, else of one in another table, else the table's
    first (neutral_model: table -> an asset to use instead, when D2R has it in that table). A source stack
    (a code of the base's three letters plus `s`) with the base's flippyfile draws the base's model, and an item
    whose flippyfile a D2R item has draws that item's model, ahead of the type's.
    borrowed gets {(table, asset): its D2R table} for each other-table picture: D2R looks an asset up in the
    item's own table's folder, so borrow_pictures copies it there. A unique or set item shows the
    D2R row it was merged onto, else its base item.
    uniques / sets: (mod name, base code, D2R name at its id or None, invfile).
    models gets {picture asset: D2R asset}: the ground model the picture's first item would borrow without it (D2R
    draws a dropped item only from its asset's model, so a sprite alone is invisible on the ground)."""
    pictures = pictures or {}
    models = {} if models is None else models
    borrowed = {} if borrowed is None else borrowed
    files = {f: _entries(hd_dir / f) for f in ("items.json", "uniques.json", "sets.json")}
    asset = {k: v["asset"] for e in files["items.json"] for k, v in e.items()}
    inv_of = {t: {r[tab.header.index("invfile")]: asset[r[tab.key]] for r in tab.rows if r[tab.key] in asset}
              for t, tab in d2r.items()}  # each table's by_inv
    for t, ptab in src.items():
        dtab = d2r[t]
        di, dt = dtab.header.index("invfile"), dtab.header.index("type")
        by_inv = {r[di]: asset[r[dtab.key]] for r in dtab.rows if r[dtab.key] in asset}
        fi = dtab.header.index("flippyfile") if "flippyfile" in dtab.header else None
        pf = ptab.header.index("flippyfile") if "flippyfile" in ptab.header else None
        by_type, by_flippy = {}, {}
        for r in dtab.rows:
            if r[dtab.key] in asset:
                by_type.setdefault(r[dt], asset[r[dtab.key]])
                if fi is not None and r[fi]:
                    by_flippy.setdefault(r[fi], asset[r[dtab.key]])
        first = next((asset[r[dtab.key]] for r in dtab.rows if r[dtab.key] in asset), None)
        if first is None:
            raise I.IdError(f"{t}: no D2R row has an items.json entry in {hd_dir}")
        if (neutral_model or {}).get(t) in asset.values():
            first = neutral_model[t]
        pi, pt = ptab.header.index("invfile"), ptab.header.index("type")
        flippy_of = {r[ptab.key]: r[pf] for r in ptab.rows} if pf is not None else {}
        for r in ptab.rows:
            code = r[ptab.key]
            base = code[:3] if code.endswith("s") and flippy_of.get(code[:3]) == flippy_of.get(code) else code
            if len(code) == 4 and not ord(code[3]) & 0x20:  # the UI sets bit 0x20 of the key's 4th byte
                raise I.IdError(f"{t} {code}: the UI keys items.json by {code[:3]}{chr(ord(code[3]) | 0x20)}, "
                                "so this code would draw no picture; give it a 4th character with bit 0x20 set")
            if code and r[pi].lower() in pictures:
                models.setdefault(pictures[r[pi].lower()],
                                  asset.get(code) or asset.get(base) or by_inv.get(r[pi])
                                  or (by_flippy.get(r[pf]) if pf is not None else None) or by_type.get(r[pt]) or first)
                asset[code] = pictures[r[pi].lower()]
                hd.set_list_entry(files["items.json"], code, {"asset": asset[code]})
            elif code and code not in asset:
                other = next((o for o in d2r if o != t and r[pi] in inv_of[o]), None)
                if r[pi] in by_inv or other is None:
                    asset[code] = by_inv.get(r[pi], first)
                else:
                    asset[code] = inv_of[other][r[pi]]
                    borrowed[(t, asset[code])] = other
                files["items.json"].append({code: {"asset": asset[code]}})
    for f, rows in (("uniques.json", uniques), ("sets.json", sets)):
        have = {k: v for e in files[f] for k, v in e.items()}
        for name, code, d2r_name, inv in rows:
            key = hd.index_key(name)
            if inv.lower() in pictures:
                found = (have.get(hd.index_key(d2r_name), {}).get("normal") if d2r_name else None) or asset.get(code)
                if found:
                    models.setdefault(pictures[inv.lower()], models.get(found, found))
                have[key] = dict.fromkeys(("normal", "uber", "ultra"), pictures[inv.lower()])
                hd.set_list_entry(files[f], key, have[key])
                continue
            if key in have:
                continue
            entry = have.get(hd.index_key(d2r_name)) if d2r_name else None
            if entry is None and code in asset:
                entry = {"normal": asset[code], "uber": asset[code], "ultra": asset[code]}
            if entry is not None:
                have[key] = entry
                files[f].append({key: entry})
    return files


def borrow_pictures(hd_dir: Path, out: Path, borrowed: dict[tuple[str, str], str]) -> None:
    """Copy each other-table D2R picture hd_items borrowed into the borrowing table's folders (hd_dir: D2R's data/hd, out:
    the mod's): the inventory sprites under global/ui/items and the ground model's unit file under items."""
    for (t, a), src_t in sorted(borrowed.items()):
        for sub, exts in ((Path("global") / "ui" / "items", (".sprite", ".lowend.sprite")), (Path("items"), (".json",))):
            for ext in exts:
                src, dest = (hd_dir / sub / hd.item_folder(x) / f"{a}{ext}" for x in (src_t, t))
                if dest.is_file():
                    raise I.IdError(f"{t}: D2R's {dest.relative_to(hd_dir)} is another picture; can't borrow {src_t}'s {a}")
                if src.is_file():
                    (out / dest.relative_to(hd_dir)).parent.mkdir(parents=True, exist_ok=True)
                    (out / dest.relative_to(hd_dir)).write_bytes(src.read_bytes())
                elif ext != ".lowend.sprite":
                    raise I.IdError(f"{src_t}: D2R has no {src.relative_to(hd_dir)}")


def ground_models(hd_items_dir: Path, out: Path, pictures: dict[str, str], models: dict[str, str],
                  uses: dict[str, set[str]]) -> None:
    """Each picture's unit file (<folder>/src/<invfile>.json), a copy of its stand-in D2R asset's from hd_items_dir: D2R
    draws a dropped item only from that file's model, so without one the item is invisible on the ground. A picture no
    item draws (a unique row with no base code) gets none."""
    for n, a in pictures.items():
        if a not in models:
            continue
        found = next((p for f in ("weapon", "armor", "misc") for p in [hd_items_dir / f / f"{models[a]}.json"]
                      if p.is_file()), None)
        if found is None:
            raise I.IdError(f"{n}: D2R has no unit file for {models[a]}")
        for t in uses[n]:
            dest = out / hd.item_folder(t) / f"{a}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(found.read_bytes())


def apply(rule: Path, src_data: Path, d2r_data: Path, out_data: Path, ctx: I.Context, vanilla: dict[str, int],
          suffix: str, upscale: Callable[[Path, dict], dict] | None = None, cube_fixes: Sequence[CUBE_FIX] = (),
          cube_after: Sequence[CUBE_FIX] = (), by_source_order: set[str] = frozenset(), source: str = "the source's",
          neutral_model: dict[str, str] | None = None
          ) -> None:
    """The merge driver's rule kind for the item-tables rule file (bind the rest with functools.partial). ctx: the
    project's Context for its id-listed tables (ids.context_of). With the three item tables merged, it also writes the
    HD item files: upscale (item_pictures) is needed when the source has pictures of its own; the rule's art cache is
    the `art/` folder beside the rule file."""
    tables, no_drop = read_rule(rule, vanilla)
    out = {}
    for t in tables:
        s, d = I.load(src_data, t), I.load(d2r_data, t)
        out[t] = (merge_cube(s, d, ctx, cube_fixes, cube_after, source=source) if t == "cubemain"
                  else merge_keyed(t, s, d, ctx, vanilla, suffix, by_source_order=by_source_order, source=source))
    if no_drop:
        if not {"treasureclassex", *ITEM_TABLES} <= set(out):
            raise I.IdError(f"{rule.name}: no-drop needs treasureclassex and {', '.join(ITEM_TABLES)} merged here")
        itemtypes = I.merge_table("itemtypes", I.load(src_data, "itemtypes"), I.load(d2r_data, "itemtypes"),
                                  ctx.lists["itemtypes"], ctx.ren)[0]
        blocked = block_drops(out["treasureclassex"], {t: out[t] for t in ITEM_TABLES}, itemtypes, no_drop)
        print(f"  never drop: {len(blocked)} items ({', '.join(sorted(no_drop))})")
    for t, merged in out.items():
        I.write(t, merged, out_data, merged.dropped, source)
    if set(ITEM_TABLES) <= set(out):
        def named(t: str) -> list[tuple[str, str, str | None, str]]:
            s, d = I.load(src_data, t), I.load(d2r_data, t).names()
            col, inv = s.header.index("code" if "code" in s.header else "item"), s.header.index("invfile")
            row = dict(zip(I.ident(s.names()), (s.rows[k] for k in s.records())))
            return [(n, row[p][col], d[i] if i < len(d) else None, row[p][inv]) for p, i, n in ctx.lists[t]]
        src, d2r = {t: I.load(src_data, t) for t in ITEM_TABLES}, {t: I.load(d2r_data, t) for t in ITEM_TABLES}
        uniques, sets = named("uniqueitems"), named("setitems")
        table_of = {r[tab.key]: t for t, tab in src.items() for r in tab.rows}
        uses: dict[str, set[str]] = {}
        for t, tab in src.items():
            for r in tab.rows:
                uses.setdefault(r[tab.header.index("invfile")].lower(), set()).add(t)
        for _, code, _, inv in uniques + sets:
            if code in table_of:
                uses.setdefault(inv.lower(), set()).add(table_of[code])
        d2r_inv = {r[k].lower() for t in [*ITEM_TABLES, "uniqueitems", "setitems"] for tab in [I.load(d2r_data, t)]
                   for k, c in enumerate(tab.header) if c.endswith("invfile") for r in tab.rows}
        if upscale is None:
            pictures = {}
            classic = src_data / "global" / "items"
            missed = sorted(n for n in uses if n not in d2r_inv and (classic / f"{n}.dc6").is_file())
            if missed:
                print(f"  WARNING: no upscaler given; {len(missed)} source pictures are not upscaled, so their "
                      f"items borrow D2R pictures ({', '.join(missed)})")
        else:
            pictures = item_pictures(upscale, rule.parent / "art", src_data, d2r_data, out_data, uses, d2r_inv)
        print(f"  item pictures: {len(pictures)} upscaled from the source's")
        models: dict[str, str] = {}
        borrowed: dict[tuple[str, str], str] = {}
        files = hd_items(d2r_data / "hd" / "items", src, d2r, uniques, sets, pictures, models, borrowed, neutral_model)
        borrow_pictures(d2r_data / "hd", out_data / "hd", borrowed)
        print(f"  other-table pictures: {len(borrowed)} ({', '.join(f'{t} {a}' for t, a in sorted(borrowed))})")
        ground_models(d2r_data / "hd" / "items", out_data / "hd" / "items", pictures, models, uses)
        for f, entries in files.items():
            dest = out_data / "hd" / "items" / f
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(entries, indent=1, ensure_ascii=False), "utf-8")
