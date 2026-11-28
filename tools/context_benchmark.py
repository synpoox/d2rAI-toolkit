"""Compare full-document, previous selective, and consolidated reading routes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from types import SimpleNamespace

from .context_budget import ENCODING, ROOT, TOKENIZER_VERSION, tokenizer
from modkit.knowledge import Index, OUTPUT_BYTES, bounded, lookup, parse_sections, render

ORIGINAL = "5d59cb6dbf6fabe34f17c8a14c73d6ddf45ba2bd"
PREVIOUS = "f491e56811073a0fb15a3499336ea9e1d4167413"
SHARED = ("templates/agents/AGENTS.md", "templates/lane-prompt.md",
          ".claude/skills/d2r-toolkit/SKILL.md")
RETRIEVAL_TOKENS = 2000


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def available(revision):
    # A squash merge leaves the earlier PR head out of main's history.
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{revision}^{{commit}}"],
                          capture_output=True).returncode == 0


def at(revision, path):
    return git("show", f"{revision}:{path}")


def count(encode, chunks):
    # Each chunk is a separate simulated read, with message framing excluded.
    return sum(len(encode(text.strip())) for text in chunks)


def previous_reads(case, revision, reference):
    plan = case["previous"]
    doc = plan["doc"]
    raw = at(revision, f"knowledge/{doc}.md")
    section = next(s for s in parse_sections(raw, doc, "knowledge") if s.title == plan["section"])
    hit = bounded(section, 0, [], OUTPUT_BYTES, "json")
    if not hit or plan["evidence"] not in hit["text"]:
        raise ValueError(f"{case['id']}: previous route lost its evidence")
    sections = {s.title: s for s in parse_sections(at(revision, reference), "reference", "skills")}
    return [*("\n".join(sections[name].lines) for name in plan["reference_sections"]), render([hit])]


def current_reads(case, index):
    output = []
    for read in case["reads"]:
        options = SimpleNamespace(lookup="get", document=read["document"], section=read["section"],
                                  start_line=None, max_bytes=OUTPUT_BYTES, format="text")
        hits = lookup(options, index)
        hit, = hits
        if hit["next_line"] is not None or not all(marker in hit["text"] for marker in read["evidence"]):
            raise ValueError(f"{case['id']}: incomplete evidence from {read['document']} / {read['section']}")
        output.append(render(hits, options.format))
    return output


def measure(original, previous, encode):
    cases = json.loads((ROOT / "docs/context-benchmark-tasks.json").read_text(encoding="utf-8"))
    index = Index(ROOT)
    rows = []
    for case in cases:
        skill = f".claude/skills/d2r-{case['skill']}/SKILL.md"
        files = (*SHARED, skill)
        doc = f"knowledge/{case['previous']['doc']}.md"
        original_tokens = count(encode, [case["prompt"], *(at(original, path).decode("utf-8")
                                                         for path in (*files, doc))])
        previous_tokens = None
        if previous:
            prior = previous_reads(case, previous, skill.replace("SKILL.md", "reference.md"))
            previous_tokens = count(encode, [case["prompt"], *(at(previous, path).decode("utf-8")
                                                             for path in files), *prior])
        retrieved = current_reads(case, index)
        retrieval_tokens = count(encode, retrieved)
        if retrieval_tokens > RETRIEVAL_TOKENS:
            raise ValueError(f"{case['id']}: {retrieval_tokens} reference tokens exceed the cumulative budget")
        current = [(ROOT / path).read_text(encoding="utf-8") for path in files]
        consolidated_tokens = count(encode, [case["prompt"], *current, *retrieved])
        reference = previous_tokens or original_tokens
        if consolidated_tokens >= reference:
            raise ValueError(f"{case['id']}: {consolidated_tokens} tokens did not improve on {reference}")
        rows.append({
            "task": case["id"],
            "original_tokens": original_tokens,
            "previous_tokens": previous_tokens,
            "consolidated_tokens": consolidated_tokens,
            "cumulative_retrieval_tokens": retrieval_tokens,
            "reduction_vs_previous_pct": previous_tokens and round(100 * (1 - consolidated_tokens / previous_tokens), 1),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=ORIGINAL, help="original full-document comparison")
    parser.add_argument("--previous", help=f"previous selective route (default {PREVIOUS}, skipped when not in history)")
    args = parser.parse_args()
    try:
        baseline = git("rev-parse", "--verify", "--end-of-options", f"{args.baseline}^{{commit}}").decode().strip()
        previous = args.previous or (PREVIOUS if available(PREVIOUS) else None)
        rows = measure(baseline, previous, tokenizer())
        head = git("rev-parse", "HEAD").decode().strip()
        dirty = bool(git("status", "--porcelain"))
    except (ImportError, OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as exc:
        print(f"context benchmark: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"method": "scripted source reads; no agent execution",
                      "tokenizer": f"tiktoken {TOKENIZER_VERSION} / {ENCODING}",
                      "original": baseline, "previous": previous, "consolidated_head": head,
                      "working_tree_dirty": dirty, "live_agent_results": None, "tasks": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
