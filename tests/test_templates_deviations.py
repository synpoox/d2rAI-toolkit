"""templates/deviations.md must feed the toolkit's own gate: a filled-in copy parses with diff.deviations()."""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.classic_import import diff  # noqa: E402

STATUSES = ("kept", "cut", "not yet", "approximated")


class TemplateDeviationsTests(unittest.TestCase):
    def test_filled_template_is_read_by_the_gate(self):
        text = (ROOT / "templates/deviations.md").read_text("utf-8")
        text = re.sub(r"`<(kept|cut|not yet|approximated)>`", r"\1", text)  # status placeholders
        text = text.replace("`<table.row.column>`", "`items.123.name`")  # the gate pattern
        text = re.sub(r"`<([^`>]*)>`", r"sample \1", text)  # every other placeholder
        text = "\n".join(l for l in text.splitlines() if not re.fullmatch(r"\|(\s*\|)+", l))  # empty rows
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deviations.md"
            path.write_text(text, "utf-8")
            patterns, entries = diff.deviations(path, STATUSES)
        self.assertEqual(patterns, ["items.123.name"])
        self.assertEqual(entries, {"kept": 1, "cut": 2, "not yet": 1, "approximated": 1})


if __name__ == "__main__":
    unittest.main()
