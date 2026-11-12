"""The local Claude Code plugin manifests stay consistent with the skills folder."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PluginManifestTest(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / ".claude-plugin" / name).read_text(encoding="utf-8"))

    def test_marketplace_lists_root_plugin(self):
        market = self.load("marketplace.json")
        plugin = self.load("plugin.json")
        self.assertTrue(market["name"] and market["owner"]["name"])
        names = [p["name"] for p in market["plugins"]]
        self.assertEqual(names, [plugin["name"]])
        self.assertEqual(market["plugins"][0]["source"], "./")

    def test_skills_path_is_folder_based_and_exists(self):
        plugin = self.load("plugin.json")
        for rel in plugin["skills"]:
            self.assertTrue(rel.startswith("./"))
            self.assertTrue((ROOT / rel).is_dir())
        self.assertTrue(list((ROOT / ".claude" / "skills").glob("*/SKILL.md")))

    def test_skill_links_use_plugin_root(self):
        bare = re.compile(r"(?<![\w/.${}-])(knowledge|templates|testing|tools|plugin-template|release|downloader|modkit|examples|third_party)/\w")
        for skill in (ROOT / ".claude" / "skills").glob("*/SKILL.md"):
            text = skill.read_text(encoding="utf-8")
            body = text.split("\n---", 1)[1]
            for line in body.splitlines():
                if line.startswith("Toolkit root:"):
                    continue
                self.assertIsNone(bare.search(line), f"{skill.parent.name}: {line}")


if __name__ == "__main__":
    unittest.main()
