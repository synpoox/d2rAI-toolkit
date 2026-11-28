"""Paired, scripted context benchmark over the same task prompts."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from types import SimpleNamespace

from .context_budget import ENCODING, ROOT, TOKENIZER_VERSION, tokenizer
from modkit.knowledge import Index, OUTPUT_BYTES, encode as evidence_json, lookup, sections

BASELINE = "5d59cb6dbf6fabe34f17c8a14c73d6ddf45ba2bd"
SHARED = ("templates/agents/AGENTS.md", "templates/lane-prompt.md",
          ".claude/skills/d2r-toolkit/SKILL.md")
RETRIEVAL_TOKENS = 2000


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args]).decode("utf-8")


def count(encode, chunks):
    # Each chunk is a separate simulated read, with message framing excluded.
    return sum(len(encode(text.strip())) for text in chunks)


def measure(baseline, encode):
    cases = json.loads((ROOT / "docs/context-benchmark-tasks.json").read_text(encoding="utf-8"))
    index = Index(ROOT)
    rows = []
    for case in cases:
        files = (*SHARED, f".claude/skills/d2r-{case['skill']}/SKILL.md")
        doc = f"knowledge/{case['doc']}.md"
        original = [git("show", f"{baseline}:{path}") for path in (*files, doc)]
        current = [(ROOT / path).read_text(encoding="utf-8") for path in files]
        reference = ROOT / files[-1].replace("SKILL.md", "reference.md")
        by_title = {section.title: section for section in sections(reference)}
        current.extend("\n".join(by_title[title].lines) for title in case["reference_sections"])
        options = SimpleNamespace(lookup="get", document=case["doc"], section=case["section"],
                                  start_line=None, max_bytes=OUTPUT_BYTES)
        hits = lookup(options, index)
        retrieved = evidence_json(hits)
        retrieval_tokens = count(encode, [retrieved])
        if retrieval_tokens > RETRIEVAL_TOKENS or not any(case["evidence"] in hit["text"] for hit in hits):
            raise ValueError(f"{case['id']}: retrieval lost expected evidence or exceeded the reference budget")
        original_tokens = count(encode, [case["prompt"], *original])
        optimized_tokens = count(encode, [case["prompt"], *current, retrieved])
        rows.append({
            "task": case["id"],
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "retrieval_tokens": retrieval_tokens,
            "reduction_pct": round(100 * (1 - optimized_tokens / original_tokens), 1),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=BASELINE)
    args = parser.parse_args()
    try:
        baseline = git("rev-parse", "--verify", "--end-of-options", f"{args.baseline}^{{commit}}").strip()
        rows = measure(baseline, tokenizer())
        head = git("rev-parse", "HEAD").strip()
        dirty = bool(git("status", "--porcelain"))
    except (ImportError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"context benchmark: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"method": "scripted source reads; no agent execution",
                      "tokenizer": f"tiktoken {TOKENIZER_VERSION} / {ENCODING}",
                      "baseline": baseline, "optimized_head": head, "working_tree_dirty": dirty,
                      "live_agent_results": None, "tasks": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
