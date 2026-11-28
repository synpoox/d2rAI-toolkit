"""Read-only validation of a mod lane against its issue and project contract."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from tools.toolkit_path import ToolkitNotFound, check_pin, find_toolkit_dir

TOOLKIT = Path(__file__).resolve().parents[1]


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if result.returncode:
        raise ValueError(f"git {args[0]} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout.decode("utf-8").rstrip("\n")


def objects(data, key):
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def strings(data, key):
    value = data.get(key)
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{key} must be an array of nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{key} contains duplicates")
    return value


def scope(data):
    paths = strings(data, "allowed_paths")
    for path in paths:
        parts = PurePosixPath(path).parts
        if not parts or any(p in (".", "..", ".git") for p in parts) or any(c in path for c in "*?[") or (
            "/".join(parts) != path.rstrip("/") or "\\" in path or ":" in path
        ):
            raise ValueError(f"invalid scope path: {path}")
    if not paths:
        raise ValueError("allowed_paths must contain at least one explicit path")
    return paths


def changed_paths(root, base):
    # With renames disabled both origin and destination must be in scope.
    commands = [
        ("diff", "--name-only", "--no-renames", "-z", base, "HEAD", "--"),
        ("diff", "--name-only", "--no-renames", "-z", base, "--"),
        ("diff", "--cached", "--name-only", "--no-renames", "-z", base, "--"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ]
    return sorted({p for cmd in commands for p in git(root, *cmd).split("\0") if p})


def in_scope(path, allowed):
    return path == allowed or (allowed.endswith("/") and path.startswith(allowed))


def inspect(root, args):
    config = tomllib.loads((root / ".d2r-project.toml").read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    project = objects(config, "project")
    repo = project.get("repo", "")
    if not isinstance(repo, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ValueError("[project].repo must be owner/name")
    if type(manifest.get("issue")) is not int or manifest["issue"] != args.issue:
        raise ValueError("manifest issue does not match --issue")
    if type(manifest.get("player_visible")) is not bool:
        raise ValueError("manifest requires a player_visible boolean")
    allowed = scope(manifest)
    checks = strings(manifest, "required_checks")
    if not checks:
        raise ValueError("manifest must name at least one acceptance check")

    problems = []
    if not (root / "toolkit.version").is_file():
        problems.append("toolkit.version is missing")
    toolkit = find_toolkit_dir(root)
    if toolkit != TOOLKIT:
        problems.append("the configured toolkit differs from the checkout running modkit")
    if problem := check_pin(root, toolkit):
        problems.append(problem)
    if git(toolkit, "status", "--porcelain"):
        problems.append("toolkit checkout has uncommitted changes")
    default = project.get("default_branch", "main")
    branches = objects(config, "branches")
    prefix = branches.get("ticket", "ticket/")
    kept = strings({"keep": branches.get("keep", ["research/*", "issue-assets", "handoff/*", "backup/*"])}, "keep")
    if not isinstance(default, str) or not default or not isinstance(prefix, str) or not prefix:
        raise ValueError("invalid default_branch or ticket prefix")
    branch = git(root, "branch", "--show-current")
    if branch == default or not re.fullmatch(re.escape(prefix) + rf"{args.issue}-[a-z0-9][a-z0-9-]*", branch):
        problems.append(f"expected a branch named {prefix}{args.issue}-<slug>")
    if any(fnmatchcase(branch, pattern) for pattern in kept):
        problems.append("lane uses a kept branch reserved for other work")
    base = git(root, "rev-parse", "--verify", "--end-of-options", f"refs/remotes/origin/{default}^{{commit}}")
    head = git(root, "rev-parse", "HEAD")
    fork = git(root, "merge-base", base, head)
    if base != fork and args.cmd == "preflight":
        problems.append(f"lane is behind local origin/{default}; check the current base")
    paths = changed_paths(root, fork)
    problems.extend(f"outside scope: {p}" for p in paths if not any(in_scope(p, a) for a in allowed))

    if args.cmd == "preflight" and args.owner and args.slot is None:
        problems.append("--owner requires --slot")
    if args.cmd == "preflight" and args.slot is not None:
        slots = objects(config, "testing").get("game_slots", [])
        if args.slot <= 1 or args.slot not in slots or not (args.owner or "").strip():
            problems.append("slot must be permitted by [testing].game_slots and have a named owner")
        else:
            result = subprocess.run(
                [sys.executable, str(toolkit / "testing/game_slots.py"), "check", str(args.slot), args.owner],
                cwd=root,
            )
            if result.returncode:
                problems.append("slot ownership check failed")

    if args.cmd == "verify-lane":
        if git(root, "status", "--porcelain"):
            problems.append("delivery requires a clean checkout")
        if head == fork:
            problems.append("lane has no commits to deliver")
        if manifest["player_visible"]:
            fragments = [p for p in paths if re.fullmatch(r"changelog\.d/[^/]+\.md", p)
                         and p.casefold() != "changelog.d/readme.md" and (root / p).is_file()]
            if not fragments:
                problems.append("player-visible change needs a changelog.d Markdown fragment")
            if "CHANGELOG.md" in paths:
                problems.append("player-visible lanes use fragments instead of editing CHANGELOG.md")
        proof = json.loads(args.evidence.read_text(encoding="utf-8"))
        if proof.get("head") != head:
            problems.append("acceptance evidence must name the current commit")
        reported = objects(proof, "checks")
        for check in checks:
            entry = objects(reported, check)
            evidence = entry.get("evidence")
            if entry.get("status") != "passed" or not isinstance(evidence, str) or not evidence.strip():
                problems.append(f"missing passed acceptance evidence: {check}")
        pr = json.loads(args.pr.read_text(encoding="utf-8"))
        if (pr.get("headRefOid"), pr.get("headRefName"), pr.get("baseRefName"), pr.get("state")) != (
            head, branch, default, "OPEN"
        ):
            problems.append("PR must be open and match the lane head, branch and configured base")
        repository = pr.get("repository")
        if not isinstance(repository, str) or repository.casefold() != repo.casefold():
            problems.append("PR repository does not match [project].repo")
        body = pr.get("body")
        if not isinstance(body, str) or not re.match(rf"^(?:Closes|Part of) #{args.issue}(?=\s|$)", body.lstrip()):
            problems.append("PR body must open with the assigned issue linkage")
        result = subprocess.run(
            [sys.executable, str(toolkit / "tools/check_public.py"), "--root", str(root), "--no-history"],
            cwd=root,
        )
        if result.returncode:
            problems.append("privacy scan failed")

    return problems


def add_parsers(sub):
    for command in ("preflight", "verify-lane"):
        p = sub.add_parser(command, help="check lane prerequisites" if command == "preflight" else
                           "validate delivery against the issue manifest")
        p.add_argument("--project", type=Path, default=Path.cwd())
        p.add_argument("--issue", required=True, type=int)
        p.add_argument("--manifest", required=True, type=Path, help="issue acceptance and scope JSON")
        if command == "verify-lane":
            p.add_argument("--evidence", required=True, type=Path)
            p.add_argument("--pr", required=True, type=Path)
        else:
            p.add_argument("--slot", type=int)
            p.add_argument("--owner")


def run(args):
    try:
        if args.issue <= 0:
            raise ValueError("--issue must be positive")
        root = Path(git(args.project, "rev-parse", "--show-toplevel")).resolve()
        problems = inspect(root, args)
    except (OSError, ValueError, AttributeError, TypeError, ToolkitNotFound) as exc:
        print(f"{args.cmd}: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"{args.cmd}: {problem}", file=sys.stderr)
    if not problems:
        print(f"{args.cmd}: OK for issue #{args.issue}")
    return int(bool(problems))
