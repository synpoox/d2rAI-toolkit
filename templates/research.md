# <Topic, as a question or a noun phrase>

Save as `docs/research/<topic>.md` on a branch named `research/<topic>`: **one research branch per ticket**. The
branch is not merged until the ticket's owner has read the answer; it is never deleted while it is the only copy. A
research document answers a question and chooses nothing; a choice becomes a decision record (`templates/ADR.md`).

Ticket: `<#n>`, part of `<#parent>`.
Question: `<the one question, in a sentence or two>`. `<What this document does not decide.>`
Read on: `<YYYY-MM-DD>` (sources below were read on this date; the answer may be stale after a game or loader update).
Target: D2R `<version>` (build `<BUILD>`), D2RLoader `<version>`, PluginSDK `<version>`.

## Sources

Pin every source so a later reader can tell whether it changed. A file in a repository is pinned by commit SHA; a file
that is not in a repository (a binary, a download, a document) by SHA-256. Give a path relative to a named root, never
an absolute path on someone's machine.

| Source | Pin | Notes |
|---|---|---|
| `<toolkit>:<path>` | `<commit sha>` | `<what was read from it>` |
| `<game file or document>` | `sha256:<hash>` | `<why this version>` |

For a research effort that reads many documents, keep a small inventory next to the research documents
(`docs/research/source-document-inventory.json`): one entry per repository with its `revision`, and per document its
`path`, `bytes`, `lines`, `sha256` and `scope` (`first-party`, `third-party`, `game`). A script regenerates it and a
check reports any document whose hash changed since it was read. Quote nothing from third-party documents beyond a
line; link them.

## Evidence labels

Tag every claim with how it is known. Use these, and add none without defining it here.

- **[doc]** a document states it (SDK README, a wiki).
- **[hdr]** only a header or an interface file shows it.
- **[data]** values read from the game's tables.
- **[RE]** a static reading of the code (decompiler), not seen running.
- **[obs]** a recorded run saw it, on this build and loader. Say where the recording is.
- **[inferred]** concluded from the others; say from which.

State what was re-run for this document and what was not.

## Short answer

Three to six bullets. The answer to the question, the cheapest thing that works, and the biggest thing still unknown.
A reader who stops here knows what to do next.

## Findings

One section per sub-question, each a table or a few bullets, each claim labelled and pointing to its source.

## Options

| Option | What it is | Cost | Risk | Evidence |
|---|---|---|---|---|
| `<A>` | `<one line>` | `<days, files touched, new tools>` | `<what could go wrong>` | `<labels>` |
| `<B>` | | | | |

**No choice made.** This document lists options; the decision is the owner's and goes in a decision record.

## Unverified

Everything above that is not **[obs]** and matters to a choice, each with the runtime check that would settle it:

| Claim | Label | Check that settles it |
|---|---|---|
| `<claim>` | `<[RE]>` | `<what to run in game, with which character or slot, and what result means yes>` |

## Follow-ups

`<Tickets to file; open questions for the owner.>`
