# Toolkit context tools

Use the pinned toolkit checkout as the working directory for the commands below. Use the skill first for mandatory constraints, then take just the references called for by the task.

## Retrieve knowledge

- **Find:** python -m modkit knowledge search "renderer pool" --limit 3
- **Read:** python -m modkit knowledge get ui-layouts --section Grids --format text
- **Get one workflow procedure:** python -m modkit knowledge get docs/testing --section "The test character" --format text
- **Look up an address:** python -m modkit knowledge address --symbol ClientFindUnit

The local index is rebuilt from the checkout on each invocation. Search and address index the knowledge base. Get can also select an existing top-level workflow document using `docs/<stem>`. Search ranks matching terms and headings. Get accepts an exact heading, anchor or a unique heading substring. Address prefers exact registry symbol/RVA rows and can also return source mentions when no row matches. A mention alone does not establish an address or ABI.

The default JSON and optional `--format text` both include the source path, heading, one-based inclusive line range, source SHA-256 and verbatim prose or table rows. Knowledge introductions carry scope and build provenance when present. Workflow excerpts include their document title. Exact address rows include the table introduction and its evidence labels when present. Read the source around an excerpt when a caveat is outside the returned lines. Follow the next line marker with get --start-line to continue; for earlier context, start at the heading.

The default limit is 8,000 bytes of output per call, a context-size proxy. The benchmark checks the sum of all reference reads for a task against a separate 2,000-token budget. You can reduce or increase the byte limit explicitly. The command exits 1 if it cannot find evidence and 2 for an invalid or ambiguous selection or an insufficient get/address budget.

## Validate a lane

Copy the accepted scope and check names from the issue into a JSON manifest outside the checkout. Use literal paths relative to the mod repo root, with a trailing slash for a directory. Wildcards are rejected. Include the changelog directory in scope if a player-facing change needs a fragment.

    {"issue":42,"allowed_paths":["patches/","changelog.d/"],
     "player_visible":true,"required_checks":["validate","runtime-stash"]}

Before work, refresh the configured origin branch, resolve the pinned toolkit, and run:

    python -m modkit preflight --project <mod> --issue 42 --manifest <manifest.json>

Preflight checks the project config, clean toolkit pin, ticket branch, locally fetched base and changed paths, including staged and untracked paths. With --slot N --owner <lane>, it checks an existing allowed slot lock using game_slots.py. It never acquires a lock. Run the normal slot ownership check again immediately before game operations as the testing skill requires.

At delivery, save the PR metadata using gh pr view --repo <owner/repo> <pr> --json headRefOid,headRefName,baseRefName,state,body and add a repository field with the same owner/name. Save a separate evidence JSON using the final full commit ID and actual observed outputs or evidence links:

    {"head":"<final full commit>",
     "checks":{"validate":{"status":"passed","evidence":"0 errors"},
               "runtime-stash":{"status":"passed","evidence":"<observed run output or evidence link>"}}}

    python -m modkit verify-lane --project <mod> --issue 42 --manifest <manifest.json> --evidence <evidence.json> --pr <pr.json>

Delivery requires a clean checkout, in-scope diff, a fragment for a player-visible change, check evidence bound to the final head, a matching open PR and a clean working-tree privacy scan. Exit 1 identifies violated checks and exit 2 identifies missing or malformed inputs. The validator checks supplied evidence against the manifest. Reviewers still verify that the inputs reflect the issue and GitHub, proof is real, generated files came from their sources, new hooks use valid signatures, and all manual constraints are met. Keep pre-commit hooks, installer guards and the merge gate in place.

## Check context budgets

Install tiktoken==0.12.0 and run python -m tools.context_budget from the toolkit root. Token counts use o200k_base. The first run downloads the tokenizer vocabulary if uncached. CI checks skill descriptions (60 tokens) and bodies (500 toolkit, 550 domain) and the startup, lane, orchestrator, handoff and reviewer templates. Review and justify any exception in context-budget-exceptions.json. The duplicate check looks for repeated substantive sentences after basic Markdown and whitespace normalization. It checks repeated sentences among entry points and between entry points and existing manuals. Historical overlap confined to manuals and paraphrases still require review.

See [benchmark methodology](context-benchmark.md) for the paired measurement and live-run protocol.
