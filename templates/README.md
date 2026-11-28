# templates: fill-in files for a mod project

Copy a file into the mod project, replace every applicable `<PLACEHOLDER>`, and delete what does not apply. Keep issue specifications in the issue, shared rules in `agents/AGENTS.md` and the referenced skills, and prompts as task invocations. New orchestrators use [setup](../docs/orchestrator-setup.md); the [rule migration ledger](../docs/context-rule-ledger.md) is for maintainers, not routine agent context. Nothing here names a
real mod. How the files fit together is in [`docs/ai-workflow.md`](../docs/ai-workflow.md).

| File | What it is for |
|---|---|
| `orchestrator-prompt.md`, `handoff.md`, `agents/AGENTS.md` (the lane rules), `lane-prompt.md`, `reviewer-prompt.md`, `owner-update.md` | Running lanes and reporting to the owner |
| `PLAN.md` | The roadmap: lettered work items, one session each, status on issues, a Blocked-by column |
| `ADR.md` | One decision record, kept at `docs/adr/NNNN-<slug>.md` |
| `deviations.md` | The deviations ledger: how a port differs from its source, one row each, feeding the table-diff gate |
| `research.md` | A research document: one `research/<topic>` branch per ticket, evidence labels, hash-pinned sources |
| `README-player.md` | Outline of the player-facing README |
| `GLOSSARY.md` | The project's terms, one definition each |
| `changelog.d/` | Changelog fragments: one small file per player-visible change (a pull request never edits `CHANGELOG.md`; the release folds the fragments in) |
| `agents/`, `d2r-project.example.toml` | `AGENTS.md` pointer pattern, issue-tracker and triage-label docs, per-project values |
| `workflows/`, `baseline.example.json` | CI and baseline examples |

## A new pass or hook is a new module with `ORDER`

When a mod's build has passes (steps that rewrite tables, strings or files in sequence), or its plugin has hooks
(patches on game functions that must run in some order), never keep them in one shared list that every change edits.
Two lanes adding a pass then edit the same lines and conflict, and the order lives nowhere you can read.

Make each pass or hook its own module, and give the module an integer `ORDER`. The runner discovers the modules,
sorts them by `ORDER`, and runs them. Every `ORDER` is unique, so the order never depends on a tie-break. Leave gaps (`ORDER = 100`,
`200`, ...) so a later pass can slot in between without renumbering.

```python
# passes/rename_ids.py
ORDER = 200          # after 100 (load), before 300 (validate)
def run(ctx): ...
```

A new pass is then a new file and no edit to anything else. A test lists the discovered modules with their `ORDER` and
fails on a duplicate `ORDER` or a module without one. The same holds in C++: each hook is its own source file that
registers itself with an `ORDER`, and the plugin applies them sorted; the plugin still checks the game build and the
expected bytes before patching (see the `d2r-engine` skill).
