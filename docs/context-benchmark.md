# Original versus optimized toolkit benchmark

Run from a checkout of the optimized revision with the original commit in its Git history:

    python -m pip install tiktoken==0.12.0
    python -m tools.context_benchmark

The task prompts and evidence expectations are in context-benchmark-tasks.json. Each arm receives the same task. The original arm simulates reading the original standing contract, lane prompt, toolkit skill, domain skill and full topic knowledge file at 5d59cb6. The optimized arm reads the current equivalent entry points, the task's relevant skill reference sections and the serialized output of one knowledge lookup. The report records the baseline, optimized checkout HEAD, whether local edits were present, and measured o200k_base input tokens, excluding any model/tool framing. Use a clean checkout for a shareable run.

This measures scripted reading routes. The original route is a full-document comparison condition, not evidence that agents always read full documents. The benchmark does not measure caching, generated tokens, actual file choices or completion. A missing evidence marker or over-budget reference read fails the static run. Markers are smoke checks for retrieval, not a score for the task.

## Live paired runs

Live agent trials have not been run. To reproduce them, pin the original and optimized checkouts, and use the same prompts, model build, settings, tool access, starting mod and game snapshots, permissions and time limit for both arms. Start fresh sessions and rotate which arm runs first. Use at least three pairs per task and record the environment and seed if the client exposes one. Let the agents choose what to load. Use disposable fixtures or permitted locked slots for game operations. Keep raw traces and private evidence out of the repository.

Record one row per trial with task ID, arm, toolkit SHA, model/settings, trial ID, elapsed time, input/cached/output tokens from the provider, tool call count, result and evidence. Use null for unavailable measurements. Have an independent reviewer apply the same rubric to both arms and record:

- Completion against the exact task prompt and acceptance requirements.
- Constraint violations, including permission, safety, scope and domain rules.
- Review findings and severity.
- Runtime checks attempted, passed, failed or skipped, plus proof or blocker.

Compare paired token and tool totals alongside completion, violations and findings. Report sample sizes, missing measurements and skipped checks. Keep scripted counts and live results in separate tables.
