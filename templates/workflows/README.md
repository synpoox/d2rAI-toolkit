# Workflow templates for a mod repository

GitHub Actions templates a mod repository copies into its own `.github/workflows/`. They are templates: nothing here
runs in the toolkit repository (Actions does not run on it), and they were reviewed by reading only. Copy one, set
the repository variables below, and replace every step marked `EDIT` with the mod's own command. Nothing mod-specific
is hard-coded; the values one mod needs are repository variables (Settings > Secrets and variables > Actions >
Variables) with the defaults shown.

| Template | What it does | Runs on |
|---|---|---|
| `tests.yml` | Unit tests of the mod's tools on synthetic fixtures, on every push to `main` and every PR. | Hosted runner |
| `gate.yml` | A table-diff style gate on every PR and push to `main`: needs the game's files, so it runs on the owner's runner. A docs-only PR runs the same job on a hosted runner and passes at once, so the required check always reports. | Self-hosted (hosted for docs-only and fork PRs) |
| `gate-control.yml` | Cancels a closed PR's gate run and reruns it when the "accept this drop" label changes. Pair of `gate.yml`. It pauses auto-merge on a label removal and leaves it paused (see below). | Hosted runner |
| `cache-verify.yml` | Nightly check that a cached build gives byte-identical output to a fresh one. | Self-hosted |
| `release.yml` | Manual full build, package and GitHub release. | Self-hosted |

Merge rule that goes with the gate (full text in the `d2r-project-conventions` skill): a docs-only PR skips it unless it
touches the gate's inputs; otherwise merge on green checks for the final head and a MERGEABLE PR. With the runner
offline, run the gate command locally on the final head and paste the report in the PR. A parity drop merges only
with the owner's "accept this drop" label (`GATE_OK_LABEL`, default `gate-drop-ok`; `[gate].drop_ok_label` in `.d2r-project.toml`).

## Why some jobs need a self-hosted runner

The game's files (and any extract of them) must never reach GitHub. A job that needs them runs on a machine the owner
controls, with a runner registered to the repository.

A fork PR can reach that runner. A `pull_request` run uses the workflow file of the PR's merge commit, so the PR can
edit `gate.yml` and set `runs-on: self-hosted` itself; the `runs-on` expression in the template only keeps honest PRs
off the runner and fails fork PRs at once, it is not a guard. The protection is repository settings: keep the
repository private, or set Settings > Actions > General > "Require approval for all external contributors", and put the
runner in a runner group limited to this repository. Never approve a fork run that touches `.github/workflows/`.

A required check that is never created stays "Expected" and blocks the PR, and a skipped one counts as passing. So
`gate.yml` has no `paths:` filter on `pull_request` and its job never skips: a `changes` job on a hosted runner finds
docs-only PRs, and the gate job runs for them on a hosted runner and ends green in its first step.

Auto-merge and the "accept this drop" label: removing the label pauses auto-merge while the gate reruns, and
`gate-control.yml` does not turn it back on. A merge made with the workflow token starts no `push` workflows, so
`gate.yml` would never run on that `main` commit and the baseline artifact would go stale. The job posts a PR comment
instead; the owner re-enables auto-merge once the gate has passed. No secret is needed.

## Repository variables

| Variable | Used by | Default | Meaning |
|---|---|---|---|
| `TEST_RUNS_ON` | tests | `["ubuntu-latest"]` | Runner labels, JSON array |
| `PYTHON_VERSION` | tests | `3.13` | Python for the unit tests |
| `TEST_DIR` | tests | `tests` | Folder `unittest discover` starts in |
| `TEST_REQUIREMENTS` | tests | none | Extra pip packages, space separated |
| `RUNNER_LABELS` | gate, cache-verify, release | `["self-hosted","windows"]` | Labels of the owner's runner, JSON array |
| `D2R_TOOLKIT` | gate, cache-verify, release | none (required) | Path of the toolkit checkout on the runner |
| `D2R_GAME` | gate, cache-verify, release | none (required) | Path of the game install (or frozen copy) on the runner |
| `MODKIT_CACHE_DIR` | gate, cache-verify, release | `<D2R_TOOLKIT>\d2r-data` | Cache of extracted game files (`MODKIT_CACHE`) |
| `DATA_LINK` | gate, cache-verify | `d2r-data` | Name of the cache junction inside the checkout |
| `RULE_CACHE_DIR` | gate, cache-verify | none (required) | Persistent shared folder of cached build results (`MODKIT_SHARED_CACHE`) |
| `GATE_CHECK_NAME` | gate, gate-control | `table-diff` | Name of the required check (the gate job's name) |
| `GATE_OK_LABEL` | gate, gate-control | `gate-drop-ok` | PR label that accepts an intended drop |
| `BASELINE_ARTIFACT` | gate | `gate-baseline` | Artifact `main` uploads and PRs compare against |
| `RELEASE_TITLE` | release | `Release` | GitHub release title prefix |
| `VERSION_FILE` | release | `mod.json` | JSON file whose `version` is the release tag |

A workflow's file name and `name:` cannot come from a variable, and neither can `on.paths`. The templates keep the
names `gate.yml` and `gate-control.yml`; rename both together, or `gate-control` stops finding the run.

## Pins

Actions are pinned to the same major versions as the toolkit's own CI (`actions/checkout@v4` and so on). Pin them to a commit SHA if the repository's
policy asks for it.
