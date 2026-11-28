"""Check the context loaded by default, with an explicit tokenizer and exception list."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCODING = "o200k_base"
TOKENIZER_VERSION = "0.12.0"
TEMPLATE_BUDGETS = {
    "templates/agents/AGENTS.md": 500,
    "templates/lane-prompt.md": 350,
    "templates/orchestrator-prompt.md": 600,
    "templates/handoff.md": 600,
    "templates/reviewer-prompt.md": 300,
}


def tokenizer():
    import tiktoken

    if tiktoken.__version__ != TOKENIZER_VERSION:
        raise ValueError(f"install tiktoken=={TOKENIZER_VERSION} for comparable counts")
    return tiktoken.get_encoding(ENCODING).encode_ordinary


def surfaces(root):
    for path in sorted((root / ".claude/skills").glob("*/SKILL.md")):
        name = path.relative_to(root).as_posix()
        empty, metadata, body = path.read_text(encoding="utf-8").split("---", 2)
        if empty or not (match := re.search(r"^description: (.+)$", metadata, re.M)):
            raise ValueError(f"{name}: expected a single-line description in frontmatter")
        yield name + ":description", match[1], 60
        yield name, body.strip(), 500 if path.parent.name == "d2r-toolkit" else 550
    for name, limit in TEMPLATE_BUDGETS.items():
        yield name, (root / name).read_text(encoding="utf-8").strip(), limit


def duplicates(documents):
    """Find substantial verbatim sentences after case, spacing and Markdown normalization."""
    by_sentence = defaultdict(set)
    for path, text in documents:
        if path.endswith(":description"):
            continue
        unwrapped = re.sub(r"\n[ \t]+", " ", text)
        for line in unwrapped.splitlines():
            if line.lstrip().startswith(("#", "|", ">", "<")):
                continue
            line = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
            for sentence in re.split(r"(?<=[.!?])\s+", line):
                normalized = " ".join(re.findall(r"[\w]+", sentence.casefold()))
                if len(normalized.split()) >= 10:
                    by_sentence[normalized].add(path)
    return {sentence: sorted(paths) for sentence, paths in sorted(by_sentence.items()) if len(paths) > 1}


def audit(root, encode, exceptions):
    rows, problems = [], []
    docs = list(surfaces(root))
    active = set()
    for name, text, budget in docs:
        tokens = len(encode(text))
        override = exceptions.get(name, {})
        limit = override.get("limit", budget)
        if override:
            active.add(name)
            if not str(override.get("reason", "")).strip() or limit <= budget or tokens <= budget:
                problems.append(f"{name}: invalid or stale budget exception")
        if tokens > limit:
            problems.append(f"{name}: {tokens} exceeds {limit} tokens")
        rows.append({"path": name, "tokens": tokens, "limit": limit})
    problems.extend(f"unknown budget exception: {name}" for name in sorted(exceptions.keys() - active))
    front_door = {name for name, _, _ in docs}
    manuals = [
        (path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
        for directory in ("knowledge", "docs", "plugin-template")
        for path in sorted((root / directory).glob("*.md"))
    ]
    inputs = [(name, content) for name, content, _ in docs] + manuals
    for sentence, paths in duplicates(inputs).items():
        if front_door.intersection(paths):
            problems.append(f"duplicate instruction ({', '.join(paths)}): {sentence}")
    return rows, problems


def main():
    try:
        exceptions = json.loads((ROOT / "docs/context-budget-exceptions.json").read_text(encoding="utf-8"))
        rows, problems = audit(ROOT, tokenizer(), exceptions)
    except (OSError, ValueError, ImportError) as exc:
        print(f"context budget: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"encoding": ENCODING, "surfaces": rows, "problems": problems}, indent=2))
    return int(bool(problems))


if __name__ == "__main__":
    sys.exit(main())
