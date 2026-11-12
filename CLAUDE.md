# d2rAI-toolkit: instructions for Claude

This repo (d2rAI-toolkit; Python package and CLI `modkit`) is a toolkit for building Diablo II: Resurrected mods, up to full overhauls, from D2R's own files and
engine. This file is for working on the toolkit itself. For working on a mod that uses it, see the `d2r-toolkit`
skill. Target: D2R 3.3 (engine addresses for build 93847 only), D2RLoader 1.3.1 (PluginSDK 0.4.0). Windows.

## Layout
`modkit/` (the Python toolkit), `knowledge/` (engine facts), `docs/`, `templates/`, `testing/`, `release/`,
`downloader/`, `plugin-template/`, `tools/` (including `tools/check_public.py`, the privacy scan, see rule 4),
`tests/`, `examples/showcase/` and `.claude/skills/`. What each holds is in the `d2r-toolkit` skill. `docs/` holds
testing.md, release.md, distribution.md and downloader.md, and the method in ai-workflow.md.

## Rules
1. **Never commit game files.** `d2r-data/` (the cache of extracted game files), mod projects' `out/` folders and
   anything copied from the game stay out of git. Blizzard's files are only read from the user's install.
2. **Engine facts:** when you learn something new about the engine (a limit, an address, a fix), add it to
   `knowledge/`. Mark build-specific values with the build number.
3. **Tests:** run `py -3 -m unittest discover tests` before a PR. Also `py -3 -m modkit build examples/showcase`
   (0 errors) if `modkit/` changed, and build the plugin template if `plugin-template/` changed. Follow
   `.github/pull_request_template.md`: one topic per pull request, link the issue.
4. **Keep the repo public-clean.** No real names, e-mails, hosts, IPs or tokens; no other projects' names. Keep a
   private-words list outside the repo (`~/.d2r-modkit/private_terms.txt`, one word per line) and run
   `python tools/check_public.py` before every commit. Commit with a noreply identity.
5. **Working with agents:** one bug or feature per lane (own branch, own worktree, PR); lanes never merge; the
   coordinator reviews, merges and releases; related bugs are merged in the bug list before fixing. Details:
   `docs/ai-workflow.md`.
6. **Plugins and installers:** `plugin-template/`, `downloader/` and `release/` code follows rule 9 of the
   `d2r-toolkit` skill: the game-image check, major.minor version checks (never a build number) and the item-type
   step.
7. **In-game checks are run by agents,** in a game slot (`testing/`, the `d2r-in-game-testing` skill), not left to
   the user. Ask the human only when a check needs one. Test characters are level 99 (experience 3520485254, 490 stat
   points, 98 skill points).
8. **Ask the human before** anything public, paid or destructive (publishing, making a repo public, force-push,
   deleting saves or branches, spending money, touching their real game install). Never ask for secrets in chat.

## Consumer guide
What the toolkit offers, where, and the craft rules a mod follows (data before code, start from vanilla, build and
validate, respect the limits, no game files in a mod, saves, plugins and the game image) are in the skill
`.claude/skills/d2r-toolkit/SKILL.md`. Keep it in step with this file when a rule that applies to both changes.
