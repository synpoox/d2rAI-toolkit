#!/bin/sh
# SessionStart hook of the d2r-toolkit plugin: warn when the checkout's HEAD does not contain origin/main.
# Warning only: always exits 0, prints nothing when the folder is not a git repo, there is no origin/main, or HEAD is
# current. Fast: the fetch is capped at 5 seconds (when `timeout` exists) and never prompts. D2R_STALE_NO_FETCH=1
# skips the fetch.
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
if [ -z "$D2R_STALE_NO_FETCH" ]; then
    export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_ASKPASS=echo SSH_ASKPASS=echo
    export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes"
    if command -v timeout >/dev/null 2>&1; then
        timeout 5 git -c credential.interactive=false fetch -q --no-auto-gc --no-auto-maintenance origin main >/dev/null 2>&1 </dev/null
    else
        git -c credential.interactive=false fetch -q --no-auto-gc --no-auto-maintenance origin main >/dev/null 2>&1 </dev/null
    fi
fi
git rev-parse --verify -q origin/main >/dev/null 2>&1 || exit 0
git merge-base --is-ancestor origin/main HEAD >/dev/null 2>&1 && exit 0
echo "WARNING: this checkout's HEAD $(git rev-parse --short HEAD) does not contain origin/main $(git rev-parse --short origin/main). Branch from or merge origin/main before building, installing a slot or opening a PR."
exit 0
