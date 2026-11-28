"""Local Markdown section index. All returned evidence is verbatim source text."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_BYTES = 8000  # Documented context proxy, independent of the user's tokenizer.
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE = re.compile(r"^ {0,3}(?:\x60{3,}|~{3,})")


def words(text):
    return set(re.findall(r"[\w]+", text.casefold()))


def anchor(title):
    return re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")


@dataclass(frozen=True)
class Section:
    doc: str
    title: str
    slug: str
    start: int
    lines: tuple[str, ...]
    provenance: tuple[str, ...]
    sha256: str
    collection: str

    def excerpt(self, first, stop):
        return {
            "source": f"{self.collection}/{self.doc}.md",
            "heading": self.title,
            "anchor": self.slug,
            "start_line": self.start + first,
            "end_line": self.start + stop - 1,
            "source_sha256": self.sha256,
            "provenance": "\n".join(self.provenance),
            "text": "\n".join(self.lines[first:stop]),
            "next_line": self.start + stop if stop < len(self.lines) else None,
        }


def sections(path, collection="knowledge"):
    raw = path.read_bytes()
    yield from parse_sections(raw, path.stem, collection)


def parse_sections(raw, doc, collection):
    lines = raw.decode("utf-8-sig").splitlines()
    headings = []
    fence = None
    for i, line in enumerate(lines):
        if match := FENCE.match(line):
            token = match[0].strip()
            if fence is None:
                fence = token
            elif token.startswith(fence) and not line[match.end():].strip():
                fence = None
            continue
        if fence is None and (match := HEADING.match(line)):
            headings.append((i, match[2]))
    if not headings or headings[0][0]:
        headings.insert(0, (0, doc))
    provenance_end = headings[1][0] if len(headings) > 1 else 1
    provenance = tuple(lines[:1 if collection == "docs" else provenance_end])
    digest = hashlib.sha256(raw).hexdigest()
    used = set()
    for (start, title), (end, _) in zip(headings, headings[1:] + [(len(lines), "")]):
        slug = base = anchor(title)
        suffix = 0
        while slug in used:
            suffix += 1
            slug = f"{base}-{suffix}"
        used.add(slug)
        if end > start:
            yield Section(doc, title, slug, start + 1, tuple(lines[start:end]), provenance, digest, collection)


class Index:
    def __init__(self, root=ROOT):
        self.root = root
        self.sections = []
        self.postings = defaultdict(set)
        self.symbols = defaultdict(list)
        for path in sorted((root / "knowledge").glob("*.md")):
            for section in sections(path):
                index = len(self.sections)
                self.sections.append(section)
                for word in words("\n".join(section.lines) + " " + section.doc):
                    self.postings[word].add(index)
                if re.fullmatch(r"d2r-\d+-addresses", section.doc):
                    for row, line in enumerate(section.lines):
                        cells = line.strip().strip("|").split("|")
                        if line.startswith("|") and len(cells) >= 2 and re.fullmatch(
                            r"\x60?0x[0-9a-fA-F]+\x60?", cells[0].strip()
                        ):
                            for key in {cell.strip(" \x60").casefold() for cell in cells[:2]}:
                                self.symbols[key].append((section, row))

    @cached_property
    def docs(self):
        return [
            section
            for path in sorted((self.root / "docs").glob("*.md"))
            for section in sections(path, "docs")
        ]

    def search(self, query):
        terms = words(query)
        candidates = set().union(*(self.postings[term] for term in terms))
        return sorted(candidates, key=lambda i: (
            -sum(i in self.postings[term] for term in terms),
            -len(terms & words(self.sections[i].title)),
            query.casefold() not in self.sections[i].title.casefold(),
            self.sections[i].doc, self.sections[i].start,
        ))

    def address(self, symbol):
        results = self.symbols.get(symbol.casefold(), [])
        if not results:
            hits = [self.sections[i].excerpt(row, row + 1)
                    for i in sorted(self.postings.get(symbol.casefold(), ()))
                    if re.fullmatch(r"d2r-\d+-addresses", self.sections[i].doc)
                    for row, line in enumerate(self.sections[i].lines) if symbol.casefold() in words(line)]
            for hit in hits:
                hit.update(match="mention", next_line=None)
            return hits
        evidence = []
        for section, row in results:
            hit = section.excerpt(row, row + 1)
            hit.update(match="registry row", next_line=None)
            # Registry labels are defined before the first data row of the coverage table.
            first_row = next(i for i, line in enumerate(section.lines)
                             if re.match(r"^\|\s*\x60?0x[0-9a-fA-F]+", line))
            hit["table_context"] = "\n".join(section.lines[:first_row])
            evidence.append(hit)
        return evidence


def encode(results):
    return json.dumps({"results": results}, ensure_ascii=True, indent=2)


def render(results, output_format="json"):
    if output_format == "json":
        return encode(results)
    blocks = []
    for hit in results:
        source = hit["source"]
        start, end = hit["start_line"], hit["end_line"]
        header = f"{source}#{hit['anchor']}:{start}-{end} (sha256 {hit['source_sha256']})"
        if "match" in hit:
            header += f" [{hit['match']}]"
        parts = [header]
        context = hit["provenance"].strip()
        excerpt = hit["text"].rstrip()
        if context and not excerpt.startswith(context):
            parts.append(context)
        table = hit.get("table_context", "").strip()
        if table:
            parts.append(table)
        parts.append(excerpt)
        if hit["next_line"] is not None:
            parts.append(f"Continue with --start-line {hit['next_line']}.")
        blocks.append("\n\n".join(parts))
    return "\n\n---\n\n".join(blocks)


def size(results, output_format):
    return len(render(results, output_format).encode("utf-8")) + 1


def bounded(section, first, results, budget, output_format):
    """Fit whole source lines, always offering a line number to resume at."""
    for stop in range(first + 1, len(section.lines) + 1):
        hit = section.excerpt(first, stop)
        if size(results + [hit], output_format) > budget:
            return previous if stop > first + 1 else None
        previous = hit
    return previous


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def add_parser(sub):
    parser = sub.add_parser("knowledge", help="retrieve cited sections and build-specific address evidence")
    commands = parser.add_subparsers(dest="lookup", required=True)
    p = commands.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=positive, default=5)
    p = commands.add_parser("get")
    p.add_argument("document", help="knowledge stem or docs/<document>")
    p.add_argument("--section", required=True, help="heading title or exact anchor")
    p.add_argument("--start-line", type=positive, help="resume from next_line in earlier output")
    p = commands.add_parser("address")
    p.add_argument("--symbol", required=True, help="exact registry symbol or hexadecimal RVA")
    for p in commands.choices.values():
        p.add_argument("--format", choices=("json", "text"), default="json",
                       help="text keeps citations and source excerpts with less formatting overhead")
        p.add_argument("--max-bytes", type=positive, default=OUTPUT_BYTES,
                       help=f"bound serialized output (default: {OUTPUT_BYTES})")


def lookup(args, index):
    output_format = args.format
    if args.lookup == "address":
        hits = index.address(args.symbol)
        if size(hits, output_format) > args.max_bytes:
            raise ValueError("address results exceed budget; use a more specific symbol or raise --max-bytes")
        return hits
    if args.lookup == "get":
        doc = args.document.removesuffix(".md").casefold()
        collection, separator, stem = doc.partition("/")
        if not separator:
            collection, stem = "knowledge", doc
        entries = index.docs if collection == "docs" else index.sections if collection == "knowledge" else ()
        choices = [s for s in entries if s.doc.casefold() == stem]
        # Prefer an exact anchor/title over a unique partial title.
        matches = [s for s in choices if args.section.casefold() == s.slug]
        if not matches:
            matches = [s for s in choices if args.section.casefold() == s.title.casefold()]
        if not matches:
            matches = [s for s in choices if args.section.casefold() in s.title.casefold()]
        if len(matches) != 1:
            raise ValueError("select a unique section: " + ", ".join(s.slug for s in (matches or choices)))
        section = matches[0]
        first = (args.start_line or section.start) - section.start
        if first < 0 or first >= len(section.lines):
            raise ValueError("--start-line is outside this section")
        hit = bounded(section, first, [], args.max_bytes, output_format)
        if hit is None:
            raise ValueError("budget cannot fit the next source line and its provenance; raise --max-bytes")
        return [hit]

    results = []
    for i in index.search(args.query)[:args.limit]:
        section = index.sections[i]
        # Keep the best hits diverse, and start at the strongest matching line within a large section.
        terms = words(args.query)
        share = max(args.max_bytes // args.limit, 1600)
        hit = bounded(section, 0, results, min(args.max_bytes, size(results, output_format) + share), output_format)
        if hit is None or hit["next_line"] is not None:
            first = max(range(len(section.lines)), key=lambda n: len(words(section.lines[n]) & terms))
            hit = bounded(section, first, results, min(args.max_bytes, size(results, output_format) + share), output_format)
        if hit is not None:
            results.append(hit)
    return results


def run(args):
    try:
        results = lookup(args, Index())
    except (OSError, ValueError) as exc:
        print(f"knowledge: {exc}", file=sys.stderr)
        return 2
    if not results:
        print("knowledge: no matching evidence within the output budget", file=sys.stderr)
        return 1
    output = render(results, args.format) + "\n"
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(output.encode("utf-8"))
    else:
        sys.stdout.write(output)
    return 0
