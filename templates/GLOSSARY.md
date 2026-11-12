# <MOD NAME>

The domain language of the project. One definition per term, in one or two sentences: what it **is**, not what it
does. Use these words in code, issues, commits and docs, and not the words under _Avoid_. When a term is argued about
in a review, settle it here. Add a term when a second person has to ask what it means.

## Language

**`<Mod name>`**:
`<What the mod is, in a sentence.>`
_Avoid_: `<other names for it>`

**`<Baseline>`** (the source):
`<The game version or mod every comparison is made against, and how it is pinned: a frozen, hash-recorded install.>`
_Avoid_: `<loose words>`

**Deviation**:
Any listed way the mod differs from the baseline, kept on purpose and checked by the table-diff gate. See
`docs/deviations.md`.
_Avoid_: exception, workaround

**Game mode**:
The rule set a D2R character is created in: Classic, Lord of Destruction or Reign of the Warlock. `<Which one(s) the
mod supports.>`

**Table set**:
One of D2R's copies of the data tables; each game mode reads its own. `<How the mod keeps them in step.>`

**Slot**:
A frozen copy of the game install used for testing, queued with locks. Slot 1 is the owner's real game and is never
touched.

**Lane**:
One bug or feature with its own branch, worktree and pull request. Lanes never merge; the coordinator does.

**`<Term>`**:
`<Definition.>`
_Avoid_: `<words not to use>`

## Relationships

- `<A Slot is used by one lane at a time.>`
- `<A Deviation cites one decision record.>`

## Flagged ambiguities

- `<"build" means the game's build number in the engine notes and a run of the mod's build script in the tooling; say "game build" or "mod build".>`
