# Roadmap

Target: Diablo II: Resurrected `<GAME VERSION>` (build `<BUILD>`) + D2RLoader `<LOADER VERSION>`.
Mod: `<MOD NAME>`. Goal: `<one sentence>`.

The roadmap orders the work. It does not track it: **status lives on the issues**, one per work item, closed by the
pull request that finishes it. Do not copy status, percentages or dates into this file; they go stale. Link the open
items with a query instead (`is:open parent-issue:<owner>/<repo>#<milestone issue>`).

## Work items

- **A work item is about one agent session**: one bug or feature, one branch, one PR. If it needs more, split it.
- **Lettered prefixes.** Each stream of work gets a prefix letter (or two), numbered on its own: `P1`, `P2`, ... for
  the data pipeline, `W1`, ... for engine rules. The "Names" table says what each prefix means and where its items are
  listed. Never reuse a number.
- **One issue per item**, titled `<prefix><n>: <what>`, a sub-issue of the milestone's issue. The issue holds the
  status and, when it closes, the PR.
- **Blocked by** names the items that must land first. An item with `none`, or whose blockers are all closed, can
  start now. Do not start a blocked item.
- **Lane** says which lane normally takes the item, so related items run one after another in one lane instead of
  conflicting.

## Names used in the roadmap

| Prefix | Meaning | Listed in |
|---|---|---|
| M1, M2 | Milestones | this file |
| `<P>` | `<e.g. data, pipeline, art, release work>` | this file |
| `<W>` | `<e.g. engine-rule work items>` | `<doc>` |

## M1: `<milestone name>`

`<One sentence: what is true when this milestone is done.>`

| # | Work item | Blocked by | Lane | Issue |
|---|---|---|---|---|
| `<P1>` | `<what it delivers, in a line>` | none | `<A>` | `<#n>` |
| `<P2>` | `<what it delivers>` | `<P1>` | `<A>` | `<#n>` |

## M2: `<milestone name>`

| # | Work item | Blocked by | Lane | Issue |
|---|---|---|---|---|
| | | | | |

## Phases a new mod usually goes through

A guide for the first milestones, not a checklist to tick here: turn each line into work items and issues.

0. **Setup.** Repository from the toolkit; toolchain; game at build `<BUILD>` with the loader; `python -m modkit fetch`
   works; game slots (slot 1 is the owner's real game and is never touched); private-words list outside the repo and
   `tools/check_public.py` passing; lane rules, coordinator prompt, bug list and `changelog.d/` from `templates/`;
   owner decisions (name, hosting, public or private, providers) recorded as decision records.
1. **Tools.** Extractors and table migration for a port's source; ID mapping layer; `python -m modkit build <project>`
   reports the baseline.
2. **Data.** Items, skills, monsters, areas, cube, strings; 0 validation errors; first boot into the character screen.
3. **Engine triage.** List every change that data cannot do and mark each `data can do it` / `plugin needed` /
   `D2R already has it` / `drop`; record what is not ported in the deviations ledger.
4. **Plugin.** Skeleton builds and loads; every hook checks the game build and expected bytes; an off switch and a
   status line per part; a game check per part; crash-safety review.
5. **Graphics.** HD first with the closest vanilla stand-ins; custom art last.
6. **Release.** Package installs like a player's install; installer with version checks; hosting; release pages;
   public repository only with the owner's approval.

## Decisions

Decisions are not kept in this file. Each is a decision record (`docs/adr/NNNN-<slug>.md`, from `templates/ADR.md`);
link the ones that shape this roadmap here:

- `<ADR 0001: title>`
