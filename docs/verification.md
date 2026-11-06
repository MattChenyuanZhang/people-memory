# Verification — 0.1.0 developer preview

Verified locally on macOS with Python 3.14 and MCP SDK 1.30.0:

- 17 automated tests pass: storage/evidence, duplicate retries, identity ambiguity and account conflicts, pause/exclusion controls, revision conflicts, resolved needs, undo dependencies, deletion/audit removal, backups, separate-process CLI retrieval, schema protection, legacy import, and two independent real stdio MCP clients sharing memory.
- Original prototype import was also exercised against a temporary destination. Active need retrieval succeeded; the original database was opened read-only.
- Source distribution and wheel built; installed-package tests run separately from editable source.

The gstack verification wrapper could not select its policy because this new repository has no origin/main or committed pregate policy. This is a wrapper setup limitation, not a passing gstack gate. The declared unittest command was run directly instead.

Not yet verified: actual model behavior in two AI products, ChatGPT remote connectivity, Windows/Linux execution, clean-machine dependency download, or public installation. CI is configured for Windows/Linux/macOS but has not run remotely. The package has not been published.

Publication review caught a profile-URL identity collision. A regression test failed before the fix and passes after preserving identity-bearing URL query/fragment components.
