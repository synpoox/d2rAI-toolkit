"""tools/probe_tables.py on a small synthetic dump (no game files)."""
import contextlib
import importlib.util
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("probe_tables", Path(__file__).resolve().parent.parent / "tools" / "probe_tables.py")
pt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pt)

BASE = 0x140000000
SPEC_JSON = {
    "build": 1,
    "anchor": {"table": "a", "slot": 1, "rva": "0x500"},
    "bounds": {"b": "0x200"},
    "tables": [
        {"name": "a", "rva": "0x100", "count": 6},
        {"name": "c", "rva": "0x180", "bound": "0x200"},
        {"name": "d", "rva": "0x1c0", "until": "0x1e0"},
    ],
}


def make_dump():
    buf = bytearray(0x300)
    put = lambda rva, v: struct.pack_into("<Q", buf, rva, v)
    for slot, target in {0: 0x600, 1: 0x500, 2: 0x600, 4: 0x700}.items():  # 3 and 5 empty, 0 and 2 share
        put(0x100 + slot * 8, BASE + target)
    struct.pack_into("<I", buf, 0x200, 2)
    put(0x180, BASE + 0x800)
    return bytes(buf)


class Probe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dump = Path(self.tmp.name, "dump.bin")
        self.dump.write_bytes(make_dump())
        self.tables = Path(self.tmp.name, "tables.json")
        self.tables.write_text(json.dumps(SPEC_JSON), encoding="utf-8")

    def run_cli(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pt.main(["--dump", str(self.dump), "--tables", str(self.tables), *extra])
        self.assertEqual(code, 0)
        return out.getvalue()

    def test_base_and_empty_and_shared(self):
        out = self.run_cli("--only", "a", "--show", "a:4,9")
        self.assertIn(f"base {hex(BASE)}", out)
        self.assertIn("null: [3, 5]", out)
        self.assertIn("'0x600': [0, 2]", out)
        self.assertIn("slot 4: 0x700", out)
        self.assertIn("slot 9: out of range", out)

    def test_bound_and_until_sizes(self):
        out = self.run_cli()
        self.assertIn("bound b @0x200 = 2", out)
        self.assertIn("c @0x180 n=2", out)
        self.assertIn("d @0x1c0 n=4", out)

    def test_wrong_dump_is_rejected(self):
        self.dump.write_bytes(bytes(0x300))
        with self.assertRaises(SystemExit):
            self.run_cli()

    def test_builtin_set_is_build_93847(self):
        self.assertEqual(pt.BUILD_93847["build"], 93847)
        self.assertTrue({"srvdo", "cltdo", "msrvhit"}.issubset({t["name"] for t in pt.BUILD_93847["tables"]}))

    def test_short_dump_is_a_clear_error(self):
        self.dump.write_bytes(make_dump()[:0x150])
        with self.assertRaises(SystemExit) as cm:
            self.run_cli()
        self.assertIn("beyond the dump", str(cm.exception))

    def test_empty_anchor_slot_is_refused(self):
        buf = bytearray(make_dump())
        struct.pack_into("<Q", buf, 0x108, 0)
        self.dump.write_bytes(bytes(buf))
        with self.assertRaises(SystemExit) as cm:
            self.run_cli()
        self.assertIn("anchor slot is empty", str(cm.exception))

    def test_unknown_show_warns_and_unverified_is_marked(self):
        spec = dict(SPEC_JSON, unverified=["c", "b"])
        self.tables.write_text(json.dumps(spec), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = self.run_cli("--show", "zzz:1")
        self.assertIn("'zzz'", err.getvalue())
        self.assertIn("bound b @0x200 = 2 (UNVERIFIED)", out)
        self.assertIn("c @0x180 n=2 (UNVERIFIED)", out)


if __name__ == "__main__":
    unittest.main()
