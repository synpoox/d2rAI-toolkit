# changelog.d: one small file per change

A pull request that changes something players notice adds a file here instead of editing `CHANGELOG.md`. Two pull
requests then never conflict on the same changelog lines. `release/stage.py` folds every `*.md` file in this folder
into the changelog when a release is made, and deletes them only after the release succeeded.

Copy this folder's idea, not this file: the project's own `changelog.d/` holds only fragments (a `README.md` there is
ignored by the release, and a `.gitkeep` keeps the folder in git when it is empty).

## A fragment

The file name is free; fragments fold in file-name order, so `<issue>-<short-name>.md` (`412-fences.md`) works. The
content is the bullet lines, in player wording, optionally under one `#### <Category>` line:

```markdown
#### Maps

- Fences are drawn low and wooden along their runs.
```

- A category that the changelog section already has gets the bullets added to it; a new one is added at the end.
- No category line: the bullets go at the end of the section, outside any category.
- One line per change, starting with a verb, in the words of a player (no file names, no internal jargon). Put the bug
  or issue number at the end, like `(#17)`. A line players must act on starts in bold (`**Restart the game.**`).
- Only bullet lines (and the one category line). No version, no date.

## Where they fold

`CHANGELOG.md` keeps a `### Unreleased` section at the top (the skeleton is at the end of this file). Fragments fold into it, or,
when you have already renamed it for the release, into `### <version> (<date>)`. A release needs that renamed section:
rename `### Unreleased` to `### <version> (<YYYY-MM-DD>)` in the release commit, then run the stager
(`release/stage.py --game <D2R folder>`). It folds the fragments in memory first, checks the section exists, packages
the mod, writes the changelog section as the release notes, and only then deletes the fragments. If anything fails, the
changelog and the fragments are exactly as before.

Paths come from `release.toml`: `repos.changelog` (default `CHANGELOG.md`) and `repos.fragments` (default
`changelog.d`).

To fold the fragments yourself (a release workflow may ask for this before it runs), use
`py -3 release/changelog.py fold --root . --version 1.2.3`: it adds them to the changelog and deletes them.

## The changelog file

Start the project's `CHANGELOG.md` with this skeleton and never edit its sections by hand except to rename
`### Unreleased` in the release commit. Each released version has exactly one section with the heading
`### <version> (<YYYY-MM-DD>)` (three `#`: the release scripts look for exactly that, and a section ends at the next
`###` or `##`). Newest first.

```markdown
# Changelog

All player-facing changes, newest first.

### Unreleased
```

A released section looks like this (the fold produces it from the fragments; `####` category headings inside it, a bold
line first if players must act):

```markdown
### 0.1.1 (2026-01-12)

**Restart the game after updating.**

#### Fixes

- Fixed a crash when entering the Den of Evil (#1).

#### Changed

- The installer now warns when another mod is set as the loader's default.
```

Guidelines for fragments, in addition to the rules above: group under `####` categories (`Fixes`, `New`, `Changed`,
or an area such as `Items`) and leave out empty ones; no internal jargon, addresses or lane names.
