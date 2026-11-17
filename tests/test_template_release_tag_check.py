"""templates/workflows/release.yml: the tag check must survive Windows PowerShell 5.1 (a missing tag is the normal case)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TemplateReleaseTagCheckTests(unittest.TestCase):
    def test_the_tag_lookup_runs_with_continue_and_reads_the_exit_code_after(self):
        text = (ROOT / "templates/workflows/release.yml").read_text("utf-8").replace("\r\n", "\n")
        steps = [r"\$ErrorActionPreference = 'Continue'", r'gh api "repos/[^\n]*git/ref/tags[^\n]*', r"\$code = \$LASTEXITCODE",
                 r"\$ErrorActionPreference = 'Stop'", r"if \(\$code -eq 0\)"]
        self.assertRegex(text, r"\n\s*".join(steps))


if __name__ == "__main__":
    unittest.main()
