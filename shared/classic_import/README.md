# classic_import: the shared classic-import package

Python code for projects that read classic Diablo II data (LoD `.mpq` archives and their `.txt` tables) to build a
D2R mod. It starts with the MPQ reader; the extract, merge and table-diff stages follow from pd2-resurrected
([#5](https://github.com/synpoox/d2rAI-toolkit/issues/5)). Only generic code goes in here: a project's own rules stay in
the project.

| Module | What it is |
| --- | --- |
| `mpq.py` | Read-only classic (v1) MPQ reader: `Archive(path).read(name)`, encrypted tables, zlib, bzip2 and PKWARE implode. No dependencies |

## Use it from a project

Put the toolkit root on `PYTHONPATH` (as for `modkit`), then:

```python
from shared.classic_import import mpq

data = mpq.Archive(install / "d2data.mpq").read("data\global\excel\skills.txt")
```

Record the toolkit commit the project was tested with, as for `shared/plugin-common` (its README, "Record the
toolkit commit").

## Tests

`python -m unittest discover tests` from the toolkit root runs `tests/test_classic_import_mpq.py` (synthetic data: no
game files needed).
