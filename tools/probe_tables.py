"""Read D2R function tables from a memory-layout dump (file offset == RVA) and report the empty and shared slots.

    py -3 tools/probe_tables.py --dump <dump.exe> [--tables my_tables.json] [--only srvdo,cltdo] [--show srvdo:41,143]

A dump (see knowledge/engine-re.md) holds the runtime pointers, so the tool first works out the runtime image base from
one anchor slot whose target RVA is known, then prints each table's empty slots (free for a plugin) and the slots that
share one target (usually a default or stub). Tables with a bound print the bound read from the dump.

The built-in table set is build 93847 only. Addresses that knowledge/d2r-93847-addresses.md confirms are plain; the ones
listed in "unverified" (cltst, msrvdmg, the srvst size, the prop and prgcalc bounds) are in no knowledge file yet and the
output marks them "(UNVERIFIED)": treat their results as leads, not facts. For another build, pass --tables with a JSON
file of the same shape as BUILD_93847 ("unverified" is an optional list of table and bound names): re-verify every
address in Ghidra first.
Read-only; stdlib only.
"""
import argparse
import json
import struct
import sys
from collections import Counter

# Build 93847 only. A table has `rva` and one size: `count`, `bound` (RVA of a u32 holding the slot count) or `until`
# (RVA where the next table starts). `bounds` lists other u32 values worth printing. `unverified` names the tables and
# bounds that no knowledge file backs yet; the output marks them.
BUILD_93847 = {
    "build": 93847,
    "anchor": {"table": "srvdo", "slot": 11, "rva": 0x5562B0},  # srvdofunc slot 11 -> this function RVA
    "unverified": ["prgcalc_bound", "cltst", "msrvdmg", "srvst", "prop_bound"],
    "bounds": {"prgcalc_bound": 0x1D1945C, "cltst": 0x235F7C0, "cltdo": 0x235F7C4, "srvhit": 0x2391404, "clthit": 0x2358A64,
               "prop_bound": 0x2386BD8},
    "tables": [
        {"name": "srvst", "rva": 0x238E710, "until": 0x238EA00},  # 91 by the dispatcher bound 0x5a; read up to the next table (94)
        {"name": "srvdo", "rva": 0x238EA00, "count": 191},
        {"name": "cltst", "rva": 0x235F590, "bound": 0x235F7C0},
        {"name": "cltdo", "rva": 0x235F7D0, "bound": 0x235F7C4},
        {"name": "msrvdo", "rva": 0x2390E80, "until": 0x2391030},
        {"name": "msrvhit", "rva": 0x2391030, "bound": 0x2391404},
        {"name": "mcltdo", "rva": 0x2358430, "until": 0x2358710},
        {"name": "mclthit", "rva": 0x2358710, "bound": 0x2358A64},
        {"name": "msrvdmg", "rva": 0x2391270, "bound": 0x2391408},
        {"name": "prop", "rva": 0x2386AB0, "bound": 0x2386BD8},
    ],
}


MAX_SLOTS = 4096


class Dump:
    def __init__(self, data):
        self.data = data

    def _read(self, fmt, rva, size):
        if rva < 0 or rva + size > len(self.data):
            raise SystemExit(f"RVA {rva:#x} is beyond the dump ({len(self.data)} bytes): not a memory-layout dump of this build")
        return struct.unpack_from(fmt, self.data, rva)[0]

    def u32(self, rva):
        return self._read("<I", rva, 4)

    def u64(self, rva):
        return self._read("<Q", rva, 8)


def table_size(d, t):
    if "count" in t:
        return t["count"]
    if "bound" in t:
        n = d.u32(t["bound"])
        if n > MAX_SLOTS:
            raise SystemExit(f"bound {t['bound']:#x} of {t['name']} reads {n}, over {MAX_SLOTS}: wrong dump or wrong build")
        return n
    return (t["until"] - t["rva"]) // 8


def find_table(spec, name):
    for t in spec["tables"]:
        if t["name"] == name:
            return t
    raise SystemExit(f"anchor table {name!r} is not in the table set")


def runtime_base(d, spec):
    a = spec["anchor"]
    t = find_table(spec, a["table"])
    slot = d.u64(t["rva"] + a["slot"] * 8)
    if slot == 0:
        raise SystemExit("anchor slot is empty: wrong dump or wrong build")
    base = slot - a["rva"]
    if base <= 0 or base & 0xFFFF:
        raise SystemExit(f"anchor gives base {base:#x}, which is not a positive 64 KiB-aligned address: wrong dump or wrong build")
    return base


def read_table(d, base, rva, n):
    vals = [d.u64(rva + i * 8) for i in range(n)]
    return [v - base if v else 0 for v in vals]


def analyse(rvs):
    """Empty slot indexes, and {target: [slots]} for targets used by more than one slot."""
    empty = [i for i, v in enumerate(rvs) if not v]
    counts = Counter(v for v in rvs if v)
    shared = {t: [i for i, v in enumerate(rvs) if v == t] for t, k in counts.items() if k > 1}
    return empty, shared


def parse_show(items):
    out = {}
    for item in items or []:
        name, _, slots = item.partition(":")
        out.setdefault(name, []).extend(int(s) for s in slots.split(",") if s)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dump", required=True, help="memory-layout dump of D2R.exe (file offset == RVA)")
    ap.add_argument("--tables", help="JSON file replacing the built-in build 93847 table set")
    ap.add_argument("--only", help="comma-separated table names to print")
    ap.add_argument("--show", action="append", metavar="TABLE:SLOT[,SLOT]", help="also print these slots' target RVAs")
    args = ap.parse_args(argv)

    spec = BUILD_93847
    if args.tables:
        with open(args.tables, encoding="utf-8") as f:
            spec = json.load(f)
        for a in spec["anchor"], *spec["tables"]:
            for k, v in list(a.items()):
                if isinstance(v, str) and k != "name" and k != "table":
                    a[k] = int(v, 0)
        spec["bounds"] = {k: int(v, 0) if isinstance(v, str) else v for k, v in spec.get("bounds", {}).items()}
    with open(args.dump, "rb") as f:
        d = Dump(f.read())

    base = runtime_base(d, spec)
    unv = set(spec.get("unverified", []))
    mark = lambda name: " (UNVERIFIED)" if name in unv else ""
    print("build", spec.get("build", "?"), "base", hex(base))
    for name, rva in spec.get("bounds", {}).items():
        print(f"bound {name} @{rva:#x} = {d.u32(rva)}{mark(name)}")
    only = set(args.only.split(",")) if args.only else None
    show = parse_show(args.show)
    printed = set()
    for t in spec["tables"]:
        if only and t["name"] not in only:
            continue
        printed.add(t["name"])
        n = table_size(d, t)
        rvs = read_table(d, base, t["rva"], n)
        empty, shared = analyse(rvs)
        print(f"\n{t['name']} @{t['rva']:#x} n={n}{mark(t['name'])}")
        print("  null:", empty)
        print("  shared targets:", {hex(k): v for k, v in shared.items()})
        for s in show.get(t["name"], []):
            print(f"  slot {s}: {rvs[s]:#x}" if 0 <= s < n else f"  slot {s}: out of range")
    for name in show:
        if name not in printed:
            print(f"warning: --show table {name!r} is not in the table set or was filtered out by --only", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
