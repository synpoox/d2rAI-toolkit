import json
import tempfile
import unittest
from pathlib import Path

from modkit.project import Build

SKILLS = "data/global/excel/skills.txt"


class FakeBase:
    """Just enough of modkit.base.Base for a build with no game files read."""

    def exists(self, rel):
        return rel == SKILLS

    def path(self, rel):
        raise AssertionError(f"build read the game's {rel}; the project layers should have supplied it")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="latin-1")


class LayerOrderTests(unittest.TestCase):
    def test_generated_after_files_and_before_patches(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            (proj / "mod.json").write_text(json.dumps({"name": "T", "savepath": "T/"}), "utf-8")
            write(proj / "files" / SKILLS, "skill\tsrvdofunc\nBash\t1\n")
            write(proj / "files/data/global/only-files.txt", "files")
            write(proj / "generated" / SKILLS, "skill\tsrvdofunc\nBash\t2\nLeap\t3\n")
            write(proj / "patches/010.json", json.dumps(
                {"ops": [{"op": "set", "table": "skills", "key": "Leap", "bank": "excel", "set": {"srvdofunc": "4"}}]}))

            Build(proj, FakeBase()).run()

            out = proj / "out"
            self.assertEqual((out / "data/global/only-files.txt").read_text(), "files")
            skills = (out / SKILLS).read_text("latin-1").splitlines()
            self.assertEqual(skills[1:], ["Bash\t2", "Leap\t4"])  # generated replaced files/, then the patch applied

    def test_no_generated_folder_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            (proj / "mod.json").write_text(json.dumps({"name": "T", "savepath": "T/"}), "utf-8")
            write(proj / "files/data/global/a.txt", "a")
            Build(proj, FakeBase()).run()
            self.assertEqual((proj / "out/data/global/a.txt").read_text(), "a")

    def test_game_copies_write_game_files_under_a_new_prefix_and_keep_project_files(self):
        class CopyBase(FakeBase):
            def list(self, prefix):
                return [prefix + "a.dcc", prefix + "sub/b.cof"]

            def bytes(self, rel):
                return rel.encode()

        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            (proj / "mod.json").write_text(json.dumps(
                {"name": "T", "savepath": "T/", "gameCopies": {"data/global/chars/am/": "data/global/monsters/am/"}}), "utf-8")
            write(proj / "files/data/global/monsters/am/a.dcc", "mine")
            Build(proj, CopyBase()).run()
            out = proj / "out/data/global/monsters/am"
            self.assertEqual((out / "a.dcc").read_text(), "mine")
            self.assertEqual((out / "sub/b.cof").read_bytes(), b"data/global/chars/am/sub/b.cof")


if __name__ == "__main__":
    unittest.main()
