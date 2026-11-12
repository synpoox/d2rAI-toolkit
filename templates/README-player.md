# <MOD NAME>

`<One or two sentences, in a player's words: what the mod is and what it changes. Say if it is offline single-player
only.>`

**Status: `<alpha 0.1.0>`** ([roadmap](docs/PLAN.md), [changelog](CHANGELOG.md), `<[how it differs from the source](docs/deviations.md)>`).

This is the outline of the README that players read first. Keep it about playing; developer material goes at the end.
The placeholders below are examples to replace or delete.

## Requirements

- Windows and Diablo II: Resurrected `<3.3.0>` (build `<BUILD>`) `<with Reign of the Warlock>`.
- [D2RLoader](https://d2rloader.net/) `<1.3.1>`. Characters load only through it.
- `<Anything else: disk space, other mods that must be off.>`

## Install

1. Close the game.
2. Unpack `<ModName>-<version>.7z` into `<D2R folder>\mods\`, so that `mods\<ModName>\<ModName>.mpq\modinfo.json`
   exists. (Or run the installer, if there is one.)
3. Make `<ModName>` D2RLoader's default mod (once).
4. Start `D2RLoader.exe`. Characters are saved in `Saved Games\Diablo II Resurrected\mods\<ModName>\`.

To update: `<what to delete or keep before unpacking the new release; what a new release overwrites>`.

## What is different

`<A short list of what players will notice, grouped. Link the changelog for the rest.>`

## Left out on purpose

`<Features of the source that are cut, one line each, with the reason. Link the deviation list for the full set.>`

## Settings and commands

`<Console commands, config files, a loot filter and where it is saved, keys.>`

## Bug reports

Found a bug? `<Open an issue at the project's tracker>` and say:

- what happened, and what you expected;
- how to make it happen again (class, level, difficulty, area, skill or item);
- the mod version (in the release's file name);
- the crash report or log, if there is one (`<where the loader writes it>`).

First check the deviation list: what is on it is known and not a bug yet.

## For developers

- Plan and open decisions: `<map issue>`
- Decisions: [`docs/adr/`](docs/adr/)
- Terms: [`GLOSSARY.md`](GLOSSARY.md)
- Research notes: [`docs/research/`](docs/research/)
- How agents and humans work here: `AGENTS.md`

No Blizzard files `<or source-mod archives>` are committed here.

## Contributing

Every pull request links its issue: the body opens with `Closes #<n>` (or `Part of #<n>`). Run the tests before you
push, and add a `changelog.d/<issue>-<slug>.md` fragment for anything a player would notice. Changes that alter
gameplay need an in-game check.

## Credits and licence

`<Credits for the source mod and its authors, with permission stated; companions and their licences; the licence of
this project's own code. This mod is not affiliated with Blizzard Entertainment.>`
