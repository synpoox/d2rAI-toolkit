"""Make the byte signatures of plugin-common's shared engine addresses from a memory-layout dump.

Every RVA declared in shared/plugin-common/src/rvas_93847/*.h gets an entry in src/sig/shared.inc: a byte pattern
with `??` wildcards that must match exactly once in the image's executable sections, and how to get the address
from the match (README.md, "Engine addresses by signature"). An entry whose pattern still finds its RVA in the dump
is kept as it is (hand-made entries survive); the others are made again. Then the cache of the dump's build,
src/sig/cache_<stamp>.inc, is written from what the patterns find.

How a pattern is made, for a code address: from the instruction holding the address (the function table in .pdata
gives the boundaries), instruction by instruction to the end of the function, with every rip-relative displacement,
rel32 branch target and image-sized displacement wildcarded, until it is unique. A function entry that is already a
jump (a D2RLoader/D2RCore hook), an address in data, and code that stays ambiguous are found through a reference
instead: a call, jump or rip-relative operand that points at it (`Rip`), or a disp32 that is the RVA itself
(`Abs`, MSVC's image-base-relative table reads); a table only read through a field offset is found through a
reference near it, the difference folded into `next`.

An entry with the pattern "" is cache only: it resolves on known builds and stays off on others. Set it by hand for
an address no code points at (D2RLoader's own slots); the script keeps it.

Usage: py -3 tools/make_signatures.py [--dump PATH] [--check]
       default dump: <MODKIT_GHIDRA_WORK or C:/ghidra-work>/D2RLoader_6ab3782c_dump.exe (tools/dump_image.py)
       --check: write nothing, exit 1 when an entry is missing or does not find its RVA
Needs capstone and numpy (py -3 -m pip install capstone numpy).
"""
import argparse
import bisect
import os
import re
import struct
import sys
from pathlib import Path

try:  # only making patterns needs them; tests import header_rvas without
    import numpy as np
    from capstone import CS_ARCH_X86, CS_GRP_BRANCH_RELATIVE, CS_MODE_64, Cs
    from capstone.x86 import X86_OP_MEM, X86_REG_RIP
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shared" / "plugin-common" / "src"
SIG = SRC / "sig"
WORK = Path(os.environ.get("MODKIT_GHIDRA_WORK") or r"C:\ghidra-work")
DECL = re.compile(r"(?:inline\s+)?constexpr\s+uint64_t\s+(\w+)(\s*\[\s*\])?\s*=\s*(\{[^}]*\}|[^;]*);", re.S)
LINE = re.compile(r'^D2R_SIG\((\w+), (\w+), (Code|Rip|Abs), (-?\d+), (\d+), "([^"]*)"\)$')
MAX_BYTES = 96  # longest pattern made; a longer one is a sign the code is not unique, use a reference


def header_rvas():
    """[(entry name, compat expression, rva, area)] in header order."""
    out = []
    for path in sorted((SRC / "rvas_93847").glob("*.h")):
        text = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8"))
        for m in DECL.finditer(text):
            values = [int(h, 16) for h in re.findall(r"0x[0-9a-fA-F]+", m.group(3))]
            if m.group(2):
                out += [(f"{m.group(1)}{i}", f"rva::{m.group(1)}[{i}]", v, path.stem) for i, v in enumerate(values)]
            else:
                # `A = 0x1, B = 0x2;` declares several
                for name, value in re.findall(r"(\w+)\s*=\s*(0x[0-9a-fA-F]+)", m.group(1) + " = " + m.group(3)):
                    out.append((name, f"rva::{name}", int(value, 16), path.stem))
    return out


class Image:
    def __init__(self, path):
        self.data = path.read_bytes()
        e = struct.unpack_from("<I", self.data, 0x3C)[0]
        self.stamp = struct.unpack_from("<I", self.data, e + 8)[0]
        count, opt = struct.unpack_from("<HH", self.data, e + 6)[0], struct.unpack_from("<H", self.data, e + 20)[0]
        self.size = struct.unpack_from("<I", self.data, e + 24 + 56)[0]
        self.exec = []  # (rva, size) of executable sections
        pdata = None
        for i in range(count):
            o = e + 24 + opt + 40 * i
            name = self.data[o:o + 8].rstrip(b"\0")
            vsize, va = struct.unpack_from("<II", self.data, o + 8)
            if struct.unpack_from("<I", self.data, o + 36)[0] & 0x20000000:
                self.exec.append((va, vsize))
            if name == b".pdata":
                pdata = (va, vsize)
        funcs = np.frombuffer(self.data, dtype="<u4", count=pdata[1] // 12 * 3, offset=pdata[0]).reshape(-1, 3)
        funcs = funcs[funcs[:, 0] != 0]
        order = np.argsort(funcs[:, 0])
        self.fstart, self.fend = funcs[order, 0].tolist(), funcs[order, 1].tolist()
        self.cs = Cs(CS_ARCH_X86, CS_MODE_64)
        self.cs.detail = True
        self._decoded = {}
        self._words = None

    def is_exec(self, rva):
        return any(va <= rva < va + size for va, size in self.exec)

    def function(self, rva):
        i = bisect.bisect_right(self.fstart, rva) - 1
        return (self.fstart[i], self.fend[i]) if i >= 0 and rva < self.fend[i] else None

    def insns(self, start, end):
        key = (start, end)
        if key not in self._decoded:
            if len(self._decoded) > 64:  # a few functions at a time: decoded instructions are large
                self._decoded.clear()
            self._decoded[key] = list(self.cs.disasm(self.data[start:end], start))
        return self._decoded[key]

    def pattern(self, insn):
        """The instruction's bytes, None where they change between builds."""
        out = list(insn.bytes)
        wild = []
        if insn.disp_size == 4 and (any(op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP for op in insn.operands)
                                    or 0x10000 <= (insn.disp & 0xFFFFFFFF) < self.size):
            wild.append((insn.disp_offset, 4))
        if insn.imm_size == 4 and insn.group(CS_GRP_BRANCH_RELATIVE):
            wild.append((insn.imm_offset, 4))
        for off, n in wild:
            out[off:off + n] = [None] * n
        return out

    def matches(self, pat, candidates=None):
        """Start RVAs where pat matches (in the executable sections); refines `candidates` when given."""
        if candidates is None:
            k, run = 0, b""  # search for the longest fixed run
            for m in re.finditer(rb"\x00+", bytes(1 if b is None else 0 for b in pat)):
                if m.end() - m.start() > len(run):
                    k, run = m.start(), bytes(pat[m.start():m.end()])
            candidates = []
            for va, size in self.exec:
                i = self.data.find(run, va, va + size)
                while i >= 0:
                    candidates.append(i - k)
                    i = self.data.find(run, i + 1, va + size)
        out = []
        for c in candidates:
            if c >= 0 and self.is_exec(c) and all(b is None or self.data[c + j] == b for j, b in enumerate(pat)):
                out.append(c)
        return out

    def words(self):
        """[(positions, int32 values)] over the executable sections, one pair per byte alignment."""
        if self._words is None:
            self._words = []
            for va, size in self.exec:
                for k in range(4):
                    n = (size - k) // 4
                    values = np.frombuffer(self.data, dtype="<i4", count=n, offset=va + k).astype(np.int64)
                    self._words.append((np.arange(n, dtype=np.int64) * 4 + va + k, values))
        return self._words


def grow(img, start, end, at, kind, nxt=0):
    """Shortest unique pattern starting at instruction `start` (inside [start, end)), or None."""
    pat, cand = [], None
    for insn in img.insns(start, min(end, start + MAX_BYTES + 16)):
        pat += img.pattern(insn)
        if len(pat) > MAX_BYTES:
            return None
        if sum(b is not None for b in pat) < 6 or len(pat) < (at + 1 if kind == "Code" else at + 4):
            continue  # too vague yet, or does not reach the address / operand
        cand = img.matches(pat, cand)
        if cand == [start]:
            return (kind, at, nxt, pat)
        if insn.mnemonic in ("ret", "int3"):
            return None
    return None


def by_code(img, rva):
    fn = img.function(rva)
    if fn is None:
        return None
    insns = img.insns(*fn)
    idx = next((i for i, x in enumerate(insns) if x.address <= rva < x.address + x.size), None)
    if idx is None:
        return None
    first = insns[idx]
    if rva == fn[0] and (first.mnemonic == "jmp" or (first.bytes[:2] == b"\x48\xb8")):
        return None  # hooked entry: its bytes are the hook's
    for back in range(0, 6):  # start a few instructions earlier when the tail alone is not unique
        if idx - back < 0:
            break
        s = insns[idx - back].address
        found = grow(img, s, fn[1], rva - s, "Code")
        if found:
            return found
    return None


def by_reference(img, rva):
    """The shortest pattern at an instruction that points at rva (or, failing that, near it: a table read through
    a field offset), starting up to 5 instructions before it."""
    sites = {}  # position -> how far the reference lands before rva (folded into `next`)
    for pos, values in img.words():
        rel = values + pos + 4
        for window in (4, 0x200):
            hit = (((rel <= rva) & (rel >= rva - window)) | (np.abs((values & 0xFFFFFFFF) - rva) <= window))
            for q in pos[hit].tolist():
                sites.setdefault(q, window)
    best = None
    for p in sorted(sites, key=lambda q: (sites[q], q))[:300]:
        if best is not None and (sites[p] > best[0] or len(best[1][3]) <= 16):
            break
        if (fn := img.function(p)) is None:
            continue
        insns = img.insns(fn[0], min(fn[1], p + 16))
        idx = next((i for i, x in enumerate(insns) if x.address <= p < x.address + x.size), None)
        if idx is None:
            continue
        insn = insns[idx]
        off = p - insn.address
        value = struct.unpack_from("<i", img.data, p)[0]
        rip = insn.group(CS_GRP_BRANCH_RELATIVE) and insn.imm_size == 4 and insn.imm_offset == off
        rip = rip or (insn.disp_size == 4 and insn.disp_offset == off
                      and any(op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP for op in insn.operands))
        absolute = not rip and insn.disp_size == 4 and insn.disp_offset == off
        if rip:
            add, kind = rva - (insn.address + insn.size + value), "Rip"
        elif absolute:
            add, kind = rva - (value & 0xFFFFFFFF), "Abs"
        else:
            continue
        if abs(add) > 0x200 or (sites[p] == 4 and add != 0):
            continue
        for back in range(0, 6):
            if idx - back < 0:
                break
            s0 = insns[idx - back].address
            nxt = (insn.address + insn.size - s0 if kind == "Rip" else 0) + add
            found = grow(img, s0, fn[1], p - s0, kind, nxt)
            if found:
                if best is None or len(found[3]) < len(best[1][3]):
                    best = (sites[p], found)
                break
    return best[1] if best else None


def text(pat):
    return " ".join("??" if b is None else f"{b:02x}" for b in pat)


def parse(s):
    return [None if t == "??" else int(t, 16) for t in s.split()]


def resolve(img, kind, at, nxt, pat):
    """The RVA the entry finds, or None when it does not match exactly once."""
    found = img.matches(pat)
    if len(found) != 1 or at < 0 or (at >= len(pat) if kind == "Code" else at + 4 > len(pat)):
        return None
    m = found[0]
    if kind == "Code":
        return m + at
    value = struct.unpack_from("<i", img.data, m + at)[0]
    return m + nxt + value if kind == "Rip" else (value & 0xFFFFFFFF) + nxt


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dump", type=Path, default=WORK / "D2RLoader_6ab3782c_dump.exe")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if np is None:
        sys.exit("needs numpy and capstone: py -3 -m pip install numpy capstone")
    img = Image(args.dump)
    shared = SIG / "shared.inc"
    old = {}
    if shared.exists():
        for line in shared.read_text(encoding="utf-8").splitlines():
            if m := LINE.match(line):
                old[m.group(1)] = (m.group(3), int(m.group(4)), int(m.group(5)), parse(m.group(6)))
    rows, cache, failed = [], [], []
    for name, compat, rva, area in header_rvas():
        entry = old.get(name)
        if entry is not None and not entry[3]:
            pass  # pattern "" by hand: cache only (an address no code points at, e.g. D2RLoader's own slots)
        elif entry is None or resolve(img, *entry) != rva:
            if args.check:
                failed.append(f"{name} {rva:#x}: {'no entry' if entry is None else 'does not find it'}")
                continue
            entry = (by_code(img, rva) if img.is_exec(rva) else None) or by_reference(img, rva)
            if entry is None or resolve(img, *entry) != rva:
                failed.append(f"{name} {rva:#x} ({area}): no unique pattern (written as cache only: decide by hand)")
                entry = ("Code", 0, 0, [])
            print(f"made {name} {rva:#x}: {entry[0]} {text(entry[3])}", flush=True)
        kind, at, nxt, pat = entry
        rows.append(f'D2R_SIG({name}, {area}, {kind}, {at}, {nxt}, "{text(pat)}")')
        cache.append(f"D2R_CACHE({name}, {compat}, {rva:#x})")
    for f in failed:
        print("FAIL", f)
    if args.check:
        print(f"{len(rows)} entries find their RVA, {len(failed)} do not")
        return 1 if failed else 0
    head = ("// Generated by tools/make_signatures.py from the build {build} dump (stamp {stamp:#010x}); hand edits are\n"
            "// kept while they still find their RVA. README.md, \"Engine addresses by signature\", explains the columns.\n")
    SIG.mkdir(exist_ok=True)
    shared.write_text(head.format(build=93847, stamp=img.stamp)
                      + "// D2R_SIG(name, area, kind, at, next, pattern)\n" + "\n".join(rows) + "\n",
                      encoding="utf-8", newline="\n")
    (SIG / f"cache_{img.stamp:08x}.inc").write_text(
        head.format(build=93847, stamp=img.stamp) + "// D2R_CACHE(name, the fixed rva:: value it must equal, rva)\n"
        + "\n".join(cache) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} entries, {len(failed)} without a pattern")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
