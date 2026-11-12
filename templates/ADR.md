# <Decision, as a short statement>

Save as `docs/adr/NNNN-<slug>.md`. `NNNN` is the next free number, four digits, never reused; the slug is the title in
lower case with hyphens. One decision per record. Keep it short: a record that needs more than a page is two decisions
or a research document (`templates/research.md`) the record links to.

Status: `<proposed | accepted | superseded by ADR NNNN | rejected>`
Date: `<YYYY-MM-DD>`
Decided by: `<owner | coordinator, with the owner's name only if the owner agrees to it being public>`
Issue: `<#n>`

## Context

What forced a decision: the situation, the constraint, the facts that matter (each with its evidence, or a link to the
research document that holds it). Say what happens if nothing is decided.

## Considered Options

- **`<Option A>`**: what it is; what it costs; what it risks.
- **`<Option B>`**: the same.
- `<Do nothing>`: include it when it is a real choice.

## Decision

The option chosen, in one or two sentences, in the present tense ("We keep D2R's inventory layouts."). Then the
reason, in a sentence or two.

## Consequences

What is now true, good and bad: what becomes easier, what becomes harder, what other documents, tools or tests change.
Name the follow-up work items.

## Amendments

Later changes to this decision are added here, newest last, each dated and linked to the issue that caused it. Do not
rewrite the sections above to hide what was first decided. If the decision is reversed, set the Status to
`superseded by ADR NNNN` and write the new record.

- `<YYYY-MM-DD> (#n): <what changed and why>`

---

How records are used (this part is not copied into the record):

- A deviation row in `docs/deviations.md` cites its record: `(ADR 0007)`. A row without a record says "decided in
  #n" until the decision is written down.
- The index is the folder listing; do not keep a second list that goes stale.
- Only the owner, or a decision the owner has delegated in writing, may set Status to `accepted`.
