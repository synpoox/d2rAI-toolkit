"""Two homes, one fact: every engine address in the per-build header has a row in the knowledge file.

shared/plugin-common/src/rvas_93847.h and rvas_93847/*.h declare RVAs as `inline constexpr uint64_t`; each hex value
(also those inside an array) must appear backticked in knowledge/d2r-93847-addresses.md.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shared" / "plugin-common" / "src"
KNOWLEDGE = ROOT / "knowledge" / "d2r-93847-addresses.md"

DECL = re.compile(r"inline\s+constexpr\s+uint64_t\s+(\w+)(\s*\[\s*\])?\s*=\s*(\{[^}]*\}|[^;]*);", re.S)
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
        known = {int(h, 16) for h in re.findall(r"`(0x[0-9a-fA-F]+)`", KNOWLEDGE.read_text(encoding="utf-8"))}
        found = header_rvas()
        self.assertGreater(len(found), 300, "the header scan found too few RVAs: has the declaration form changed?")
        missing = sorted(f"{name} {value:#x} ({file})" for value, (name, file) in found.items() if value not in known)
        self.assertEqual(missing, [], "RVAs without a row in knowledge/d2r-93847-addresses.md")

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
