"""templates/workflows/tests.yml: the lint step is optional and runs only when RUFF_VERSION is set."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TemplateTestsRuffTests(unittest.TestCase):
    def test_ruff_step_is_gated_on_the_variable(self):
        text = (ROOT / "templates/workflows/tests.yml").read_text("utf-8")
        step = text.split("- name: Ruff", 1)[1]
        self.assertIn("if: ${{ vars.RUFF_VERSION != '' }}", step)
        self.assertIn("ruff check", step)

    def test_variables_are_documented(self):
        readme = (ROOT / "templates/workflows/README.md").read_text("utf-8")
        for name in ("RUFF_VERSION", "RUFF_DIR"):
            self.assertIn(f"`{name}`", readme)


if __name__ == "__main__":
    unittest.main()
