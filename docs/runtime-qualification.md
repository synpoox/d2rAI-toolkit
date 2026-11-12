# Qualifying a game and loader combination

Before a mod claims "works on D2R 3.3 with D2RLoader x.y", test that exact combination and write the result down.
Choosing a combination is not evidence that it works. This page is the checklist, and the rules for what a result is
worth when the loader updates.

Contents: [Choosing a loader policy](#choosing-a-loader-policy) · [What to record](#what-to-record) · [The checklist](#the-checklist) ·
[Source notes](#source-notes)

## Choosing a loader policy

A mod on a fixed game build (this toolkit targets D2R 3.3, Windows, Battle.net, build 93847, and D2RLoader 1.3.1)
picks how it follows the loader. Both options are workable; they differ in what they cost.

| Option | Consequences |
|---|---|
| Rolling latest official release (betas included) | Every new release must be requalified before the mod calls it verified, and a passing record for an older release is history. Players get loader fixes sooner. Hook addresses and service sizes can change under the mod. If the newest loader stops working with the game, the combination is incompatible until the mod or the loader is fixed |
| Pinned release | Hook addresses, service sizes and test results stay stable, and one record covers the shipped combination. Fixes in later loader releases are missed, and moving the pin takes a deliberate bump and a requalification |

Whichever you choose, a passing record qualifies only the exact release tested: a newer version number inherits
nothing. A combination stays "selected, pending qualification" until a run passes. The game build is part of the
claim too. Steam and Wine are untested here: a Steam build has been seen running the same program image under another
build number ([d2rloader.md](../knowledge/d2rloader.md), "Versions and builds"), but equality of hook addresses and
table data is a finding for the test host, not an assumption. An unreleased nightly channel has no stable identity to
record.

## What to record

One record per run, so the check can be repeated:

| Field | Notes |
|---|---|
| Game | store, complete version and build, `D2R.exe` SHA-256, the data identity (`dataversionbuild.txt`) |
| Host | Windows version |
| Loader | official source URL, version, published verification metadata, archive SHA-256, and the identity of the extracted files |
| Setup | every loader setting, built-in patch and extension that was on |
| Inputs | the mod folder or archive hash, plugin versions, procedure, logs |
| Result | each check passed, failed, or not run, with the reason; the date; the newest release you checked |

## The checklist

Baseline qualification proves launch, data loading, and offline save and reload. It does not prove gameplay balance,
multiplayer, or any plugin's hooks: those need their own checks.

1. **Identify the install.** Confirm the store, build and executable hash yourself. Do not infer the build from a
   version shorthand such as "3.3".
2. **Resolve the loader at test time.** Use the newest official release then, not the one you saw last month. Verify the
   download against the published metadata and record its hashes.
3. **Isolate.** Use a test copy or a game slot ([testing.md](testing.md)), record every setting, and capture evidence of
   the actual game and loader versions from the log.
4. **Load a minimal data mod.** Put an observable marker in a representative table, let the loader compile the tables,
   and show that the intended bank and table are the ones the game uses (see "Two banks" in
   [tables.md](../knowledge/tables.md)). Keep the inputs.
5. **Save and reload.** Create a disposable offline character, give it identifiable items in inventory and stash,
   save, exit, relaunch, reload. Compare expected and observed state; keep the logs and errors.
6. **Write the record.** It passes only when every baseline check succeeded without unexplained failures. List failed
   checks, missing prerequisites and untested surfaces; do not mark the combination qualified with checks missing.
7. **If the mod ships a plugin,** add probes for the SDK services and hooks it needs, against the loader you qualify.
   Matching ABI numbers alone do not establish that the interface is compatible. Refuse to activate a plugin whose
   hooks do not verify ([plugin-template/README.md](../plugin-template/README.md)).
8. **On every new loader release,** repeat steps 2 to 6 for the checks the release could affect, before saying it
   is verified.

Needs: a Windows host with an owned install of the target build, the current loader release and its metadata, and
permission to run a disposable mod with disposable characters and stashes.

## Source notes

Conflicts between published sources, as found when this checklist was written (2026-11); re-check before relying on
them.

| Claim | What the sources show |
|---|---|
| First loader with D2R 3.3 support | The loader's official changelog places it in **1.2.0-beta**; an earlier research note said 1.3.0-beta. [d2rloader-capabilities.md](../knowledge/d2rloader-capabilities.md) now follows the changelog reading. The changelog was not re-fetched when this was reconciled |
| SDK version of loader 1.3.1-beta | The SDK header reports SDK 0.4.0 / ABI 4; the loader's release notes report SDK 0.3.0 / ABI 4. Observations, not a selection |
| Game version the loader targets | The loader wiki's overview names an older 3.1 build, which conflicts with newer explicit 3.3 support. The wiki's table research reports testing 3.3.0 build 93847 and leaves other builds unchecked. Neither is a qualification of your mod |
| A third-party suite's requirements | List build 93847 and a Steam build: evidence for that component, not a guarantee that code and data layouts are identical |
