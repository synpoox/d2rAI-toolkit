"""Every shared engine RVA has a signature entry and a build 93847 cache row with the same value (no game files).

The entries (shared/plugin-common/src/sig/shared.inc) and the cache (sig/cache_6ab3782c.inc) come from
tools/make_signatures.py; a new rva:: value in rvas_93847/ needs its entry: rerun the script on the build's dump.
That every pattern finds its RVA in the dump is plugin-common's sig_dump_test.
"""
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("make_signatures", ROOT / "tools" / "make_signatures.py")
ms = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ms)


class SignaturesTest(unittest.TestCase):
    def test_every_rva_has_an_entry_and_a_cache_row(self):
        rvas = ms.header_rvas()
        self.assertGreater(len(rvas), 300, "the header scan found too few RVAs: has the declaration form changed?")
        entries = [m.group(1) for line in (ms.SIG / "shared.inc").read_text(encoding="utf-8").splitlines()
                   if (m := ms.LINE.match(line))]
        cache = dict(re.findall(r"^D2R_CACHE\((\w+), [^,]+, (0x[0-9a-f]+)\)$",
                                (ms.SIG / "cache_6ab3782c.inc").read_text(encoding="utf-8"), re.M))
        self.assertEqual(entries, [name for name, _, _, _ in rvas], "sig/shared.inc is not the header's RVAs in order")
        self.assertEqual({k: int(v, 16) for k, v in cache.items()}, {name: rva for name, _, rva, _ in rvas})

    def test_patterns_are_well_formed(self):
        for line in (ms.SIG / "shared.inc").read_text(encoding="utf-8").splitlines():
            if line.startswith("D2R_SIG"):
                m = ms.LINE.match(line)
                self.assertIsNotNone(m, line)
                pat = m.group(6).split()
                if not pat:
                    continue  # cache only
                self.assertTrue(all(re.fullmatch(r"[0-9a-f]{2}|\?\?", t) for t in pat), line)
                self.assertLessEqual(len(pat), 256, line)
                at = int(m.group(4))
                self.assertLess(at if m.group(3) == "Code" else at + 3, len(pat), line)


if __name__ == "__main__":
    unittest.main()
