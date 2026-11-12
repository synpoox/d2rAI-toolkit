"""Two homes, one fact: every engine address in the per-build header has a row in the knowledge file.

shared/plugin-common/src/rvas_93847.h and rvas_93847/*.h declare RVAs as `constexpr uint64_t` (with or without
`inline`); each hex value (also each element of an array) must be backticked in the FIRST cell of a table row of
knowledge/d2r-93847-addresses.md. A mention in another row's prose does not count. A row may key several RVAs
(`0xa` / `0xb`), so an array lists all its elements in its row's first cell.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shared" / "plugin-common" / "src"
KNOWLEDGE = ROOT / "knowledge" / "d2r-93847-addresses.md"

DECL = re.compile(r"(?:inline\s+)?constexpr\s+uint64_t\s+(\w+)(\s*\[\s*\])?\s*=\s*(\{[^}]*\}|[^;]*);", re.S)
FIRST_CELL = re.compile(r"^\|([^|]*)\|")
HEX = re.compile(r"0x[0-9a-fA-F]+")


def header_rvas():
    files = [SRC / "rvas_93847.h", *sorted((SRC / "rvas_93847").glob("*.h"))]
    found = {}
    for path in files:
        text = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8"))
        for m in DECL.finditer(text):
            for h in HEX.findall(m.group(3)):
                found.setdefault(int(h, 16), (m.group(1), path.name))
    return found


class RvaKnowledgeTest(unittest.TestCase):
    def test_every_header_rva_has_a_knowledge_row(self):
        known = set()
        for line in KNOWLEDGE.read_text(encoding="utf-8").splitlines():
            m = FIRST_CELL.match(line)
            if m:
                known.update(int(h, 16) for h in re.findall(r"`(0x[0-9a-fA-F]+)`", m.group(1)))
        found = header_rvas()
        self.assertGreater(len(found), 300, "the header scan found too few RVAs: has the declaration form changed?")
        missing = sorted(f"{name} {value:#x} ({file})" for value, (name, file) in found.items() if value not in known)
        self.assertEqual(missing, [], "RVAs without a table row keyed by them in knowledge/d2r-93847-addresses.md")

    def test_coverage_rows_are_well_formed(self):
        text = KNOWLEDGE.read_text(encoding="utf-8")
        section = text[text.index("## Header coverage") :]
        row = re.compile(r"^\| `0x[0-9a-f]+`(?: / `0x[0-9a-f]+`)* \| (\S+) \| (.*?) \| (.*) \| ([A-Z]) \|$")
        rows = [m for m in map(row.match, section.splitlines()) if m]
        self.assertGreater(len(rows), 200)
        bad = []
        for m in rows:
            name, sig, meaning, ev = m.groups()
            if sig.count("(") != sig.count(")") or meaning.count("(") != meaning.count(")"):
                bad.append(f"{name}: unbalanced parentheses")
            if sig != "-" and sig == meaning:
                bad.append(f"{name}: the meaning repeats the signature")
            if re.match(r"^(txt|cpp|13c|\.|\)|dll)\b", meaning):
                bad.append(f"{name}: the meaning starts mid-word (a split at a dot)")
            if ev not in "HCTRPD":
                bad.append(f"{name}: unknown evidence {ev}")
        self.assertEqual(bad, [])

    def test_umbrella_includes_every_area(self):
        umbrella = (SRC / "rvas_93847.h").read_text(encoding="utf-8")
        for area in sorted((SRC / "rvas_93847").glob("*.h")):
            self.assertIn(f'#include "rvas_93847/{area.name}"', umbrella)

    def test_policy_line_in_header_and_readme(self):
        needle = "d2r-93847-addresses.md"
        self.assertIn(needle, (SRC / "rvas_93847.h").read_text(encoding="utf-8"))
        self.assertIn(needle, (ROOT / "shared" / "plugin-common" / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
