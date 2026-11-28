---
name: d2r-release
description: Release a Diablo II Resurrected mod after a merged batch. Use for version bumps, fragment changelogs, packaging, publishing, installer or launcher distribution and closing released issues.
---

# Release a mod version

1. Read [Before you start](reference.md#before-you-start). Verify owner authorization, merged fixes, release-like checks, privacy and an idle checkout. Capture the commit and keep the checkout on it during the run.
2. Follow [Steps](reference.md#steps). Bump the version once, derive notes from fragments and run the single fail-fast build/publish/verify script. Capture output without piping publish through filters. Verify the live version before public pages or mirrors. Use major.minor for game requirements.
3. For GitHub launcher assets, read [Launcher release](reference.md#releases-for-the-resurrected-launcher-github-assets) and use its dry run and draft verification. For Nexus or public mirrors read [distribution](../../../docs/distribution.md) and [Public mirror](reference.md#public-mirror).
4. On failure follow [If it fails](reference.md#if-it-fails). Verify the published package in a release-like slot and check the reported version and release status. Close fixed issues with the version and send the owner the release link.
