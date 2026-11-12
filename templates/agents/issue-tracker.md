# Issue tracker: GitHub

Issues and specs live in this repository's GitHub Issues (`[project].repo` in `.d2r-project.toml`). Use `gh`.

Before creating anything, verify the destination with `gh repo view --json nameWithOwner`: it must match
`[project].repo`. File issues only there.

## Operations

- Create: `gh issue create --title "..." --body-file <file>`. Use a file with real newlines for multi-line bodies.
- Read: `gh issue view <number> --json number,title,body,labels,comments`.
- List: `gh issue list --state open`; filter with `--label`.
- Comment: `gh issue comment <number> --body-file <file>`.
- Labels: `gh issue edit <number> --add-label "..." --remove-label "..."`.
- Close: post the explanation first (a separate comment), then `gh issue close <number>`. Comment separately even
  when the issue is already closed.

## Sub-issues and blockers

Link through the API, not only in text. A `Part of #n` line or a comment alone does not make the link.

- Sub-issue: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>` (`gh` 2.94+).
  Older `gh`: `gh api -X POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`.
- Blocker: `gh issue edit <child> --add-blocked-by <blocker>`. Older `gh`: `gh api -X POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`.
- `<db-id>` is the numeric **database id**, not the `#number` or `node_id`: `gh api repos/<owner>/<repo>/issues/<n> --jq .id`.
- Where the API is unavailable, put `Part of #<parent>` and `Blocked by: #<n>` at the top of the body and list
  children in the parent's task list. A ticket is unblocked when every blocker is closed.

## Pull requests link their issue

Every PR body opens with the issue it solves: `Closes #<n>` when merging finishes it, `Part of #<n>` when it does
not. A PR with no issue gets one opened first.

## Pull requests as a triage surface

**PRs as a request surface: no.** (Mirrors `[issues].prs_are_triage_surface`. When `true`, PRs run through the same
labels as issues with the `gh pr` equivalents: `gh pr view --comments`, `gh pr diff`, `gh pr comment`, `gh pr edit`, `gh pr close`.)

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: try `gh pr view 42`, then `gh issue view 42`.

## Skill conventions

"Publish to the issue tracker" means create a GitHub issue. "Fetch the relevant ticket" means read the GitHub issue.
