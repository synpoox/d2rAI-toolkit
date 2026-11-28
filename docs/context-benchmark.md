# Original, previous and consolidated context

From a checkout containing the PR history, run:

    python -m pip install tiktoken==0.12.0
    python -m tools.context_benchmark

The same task prompts and acceptance requirements are recorded in [the task manifest](context-benchmark-tasks.json). Each arm counts the prompt, the startup contract, lane prompt and toolkit and domain skills, plus these reads:

| Arm | Additional reads |
|---|---|
| Original (5d59cb6) | The full topic knowledge file |
| Previous PR (f491e56) | The same skill-local sections and JSON knowledge excerpt as the previous PR's benchmark |
| Consolidated | All listed calls to `modkit knowledge get --format text`, with citations, for the workflow and technical sections the task needs |

The read plan charges for **every listed read**, including repeated provenance and citation text. It includes both the entry guides and the references. Each task must improve on the previous selective route, return all expected evidence in complete sections and stay within 2,000 cumulative reference tokens. The previous arm's excerpt is JSON (its only format), the consolidated reads use text, so part of the gain is serialization. Counts use o200k_base and exclude provider message framing, caching and generated text. The runner records the commits and whether local edits are present. Source fingerprints can tokenize slightly differently across checkout line-ending settings.

This is a scripted comparison of cumulative instructional input, using stronger evidence than a file-size comparison but still a proxy for agent consumption. An agent may choose a different read plan. Smoke markers prove the selected sections contain expected details. They cannot establish task correctness, completion or compliance.

## Live paired runs

Live agent trials have not been run. Pin the previous PR and consolidated revisions and use the same prompts, model build, settings, tools, starting mod and game snapshots, permissions and time limit for both arms. Start fresh sessions and rotate which arm runs first. Use at least three pairs per task and record the seed if the client exposes one. Let agents choose what they load. Use disposable fixtures or permitted locked slots for game operations. Keep raw traces and private evidence out of the repository.

Record task ID, arm, toolkit SHA, model/settings, trial ID, elapsed time, input/cached/output tokens from the provider, tool call count, result and evidence. Use null for unavailable measurements. Have an independent reviewer apply the same task rubric to both arms and record:

- Completion against the exact task prompt and acceptance requirements.
- Constraint violations, including permission, safety, scope and domain rules.
- Review findings and severity.
- Runtime checks attempted, passed, failed or skipped, with proof or blocker.

Compare paired token and tool totals alongside completion, violations and findings. Report sample sizes, missing measurements and skipped checks. Keep scripted counts and live results in separate tables.
