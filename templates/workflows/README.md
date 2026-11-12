# Workflow templates for a mod repository

GitHub Actions templates a mod repository copies into its own `.github/workflows/`. They are templates: nothing here
runs in the toolkit repository (Actions does not run on it), and they were reviewed by reading only. Copy one, set
the repository variables below, and replace every step marked `EDIT` with the mod's own command. Nothing mod-specific
is hard-coded; the values one mod needs are repository variables (Settings > Secrets and variables > Actions >
Variables) with the defaults shown.

| Template | What it does | Runs on |
|---|---|---|
| `tests.yml` | Unit tests of the mod's tools on synthetic fixtures, on every push to `main` and every PR. | Hosted runner |
| `gate.yml` | A table-diff style gate on every PR and push to `main`: needs the game's files, so it runs on the owner's runner. | Self-hosted |
| `gate-control.yml` | Cancels a closed PR's gate run and reruns it when the "accept this drop" label changes. Pair of `gate.yml`. | Hosted runner |
| `cache-verify.yml` | Nightly check that a cached build gives byte-identical output to a fresh one. | Self-hosted |
| `release.yml` | Manual full build, package and GitHub release. | Self-hosted |

## Why some jobs need a self-hosted runner

The game's files (and any extract of them) must never reach GitHub. A job that needs them runs on a machine the owner
controls, with a runner registered to the repository. Keep that runner for the repository's own branches only: a PR
from a fork would run the fork's code on that machine, so the gate template fails fork PRs at once on a hosted runner
(a skipped required check counts as passing, so the job must never skip).

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
| `RULE_CACHE_DIR` | gate, cache-verify | `<runner temp>\rule-cache` | Shared folder of cached build results |
| `GATE_CHECK_NAME` | gate, gate-control | `table-diff` | Name of the required check (the gate job's name) |
| `GATE_OK_LABEL` | gate, gate-control | `gate-drop-ok` | PR label that accepts an intended drop |
| `BASELINE_ARTIFACT` | gate | `gate-baseline` | Artifact `main` uploads and PRs compare against |
| `RELEASE_TITLE` | release | `Release` | GitHub release title prefix |
| `VERSION_FILE` | release | `mod.json` | JSON file whose `version` is the release tag |

A workflow's file name and `name:` cannot come from a variable, and neither can `on.paths`. The templates keep the
names `gate.yml` and `gate-control.yml`; rename both together, or `gate-control` stops finding the run.

## Pins

Actions are pinned to major versions (`actions/checkout@v4` and so on). Pin them to a commit SHA if the repository's
policy asks for it.
