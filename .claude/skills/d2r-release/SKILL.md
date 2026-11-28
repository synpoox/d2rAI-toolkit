---
name: d2r-release
description: Release a Diablo II Resurrected mod after a merged batch. Use for version bumps, fragment changelogs, packaging, publishing, installer or launcher distribution and closing released issues.
---

# Release a mod version

1. Get owner authorization. Verify merged fixes, targeted and release-like checks, clean privacy scan and idle checkout. Capture HEAD and keep the checkout fixed during release. Read [Before you release](../../../docs/release.md#before-you-release) for config and prerequisites.
2. Bump the version once. Derive release notes from fragments. Run one fail-fast [release script](../../../docs/release.md#releasesh) to check version/changelog/plugin agreement, build without the harness, publish with the current installer, verify live version, then create pages. Never pipe publish output through filters. Installer requirements use game major.minor.
3. For launcher assets follow [schema 3](../../../docs/release.md#launcher-release-schema-3), including dry run and authorization before public publication. If mirroring, follow [distribution](../../../docs/distribution.md) or [public mirror procedure](../../../tools/publish_mirror.md) after the version is live.
4. Stop on first failure and follow [publication recovery](../../../docs/release.md#recover-a-failed-publication); repair and rerun in order. In a release-like slot check startup status/version and `(release)`. Comment with the released version before closing issues, then give the owner the release link.
