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


if __name__ == "__main__":
    unittest.main()
