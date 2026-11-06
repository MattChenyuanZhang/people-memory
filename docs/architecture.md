# Architecture and limits

The installed package has one model-independent memory engine, a CLI, and a thin MCP adapter. There is no network listener or model call in the core. MCP uses the official Python SDK 1.x FastMCP implementation and stdio transport. Tools return JSON-compatible records rather than generating answers.

## SQLite storage

The original prototype's logical entities are preserved, but the distributable uses a separate versioned schema rather than mutating the personal prototype database. The explicit importer translates old normalized rows into versioned documents and preserves legacy provenance. The original file remains untouched.

`entities` stores persons, interactions, observations and imported source metadata as JSON documents with stable IDs, owners, revisions and deletion tombstones. Observations link to original interactions. `changes` and `mutations` preserve before-images for each transaction. FTS5 indexes active documents through triggers. `settings` stores shared recording preferences. Schema version lives in `PRAGMA user_version`; unsupported versions are rejected before migration.

BEGIN IMMEDIATE serializes writers. Every interaction write is atomic, including person, interaction, observations and audit journal. Corrections require current revisions. Undo checks every touched revision and later dependent interactions before restoring anything; it refuses conflicts atomically. It is intentionally conservative: undoing a newer edit does not reset revisions to old numbers, so an older undo may still require manual correction.

## Identity and retrieval

Confirmed account URLs are stronger identity anchors than names. Multiple matching accounts that disagree cause a refusal. Name-only collisions cause clarification. Unknown dates remain null. Full-text search uses OR tokens to retrieve candidates; clients can filter categories and statuses and expand related words. It isn't an embedding engine. JSON keys are indexed alongside values in this preview, which can add noise; assistants must inspect evidence before answering.

## Trust boundaries

The host assistant sees user messages and attachments. It decides what is real, permitted to save, which person is meant, and how to extract source-backed facts. The server receives only tool arguments. It cannot independently verify user intent, /record, don't-save instructions or screenshot transcription. It enforces mechanical validation and shared pause state, not semantic truth. Read/write annotations are hints to clients, not authorization controls.

Only a client-side trusted message hook could guarantee every-message processing or strictly enforce a textual trigger. The preview doesn't claim either. File access and tool approval are controlled by the host/client.

## Not included

Authenticated remote hosting, cloud account isolation, original file attachment storage, automatic LinkedIn/X extraction, a chat UI, embeddings, background monitoring, platform signing, package-registry publication, live two-model evaluations, and export restoration. Model-generated memory can be wrong; source evidence and correction are essential.
