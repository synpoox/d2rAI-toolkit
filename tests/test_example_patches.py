import json
import unittest
from pathlib import Path

from modkit.project import OPS

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "patches"


class ExamplePatchTests(unittest.TestCase):
    """Every example patch is valid JSON and uses only ops modkit knows (no game files needed)."""

    def test_ops_are_known(self):
        files = sorted(EXAMPLES.glob("*.json"))
        self.assertTrue(files, "no example patches found")
        for f in files:
            doc = json.loads(f.read_text("utf-8"))
            ops = doc["ops"] if isinstance(doc, dict) else doc
            self.assertTrue(ops, f.name)
            for n, op in enumerate(ops):
                self.assertIn(op.get("op"), OPS, f"{f.name} op {n}")

    def test_json_ops_have_path_and_value(self):
        for f in EXAMPLES.glob("*.json"):
            for op in json.loads(f.read_text("utf-8"))["ops"]:
                if op["op"] == "json":
                    self.assertIsInstance(op["path"], list, f.name)
                    self.assertIn("value", op, f.name)
                    self.assertTrue(op["file"].startswith("data/"), f.name)

    def test_terror_zone_patch_covers_all_combinations(self):
        doc = json.loads((EXAMPLES / "no-terror-zones.json").read_text("utf-8"))
        seen = set()
        for op in doc["ops"]:
            if op["op"] == "json" and op["file"].endswith("desecratedzones.json"):
                path = op["path"]
                self.assertEqual(path[:3], ["desecrated_zones", 0, "game_difficulties"])
                seen.add(tuple(path[3:]))
        want = {(m, d, f) for m in ("expansion", "rotw") for d in ("normal", "nightmare", "hell")
                for f in ("ladder_enabled", "non_ladder_enabled", "max_herald_tiers")}
        self.assertEqual(seen, want)


if __name__ == "__main__":
    unittest.main()
