# People Memory

External relationship memory for AI assistants. Talk naturally about real interactions; your connected assistant records source-backed information, recalls it later, and reasons about useful introductions.

**Version 0.1.0 is a local developer preview.** The storage engine, command-line interface, and stdio MCP server work. Two independent MCP SDK clients are integration-tested; live ChatGPT, Claude Desktop, and Codex conversations have not yet been validated. No GUI, hosted service, or automatic social-message sync is included.

## Connect to an AI app

Install People Match below, then choose your app:

- **[Claude Desktop](docs/connecting.md#claude-desktop)** — local configuration file.
- **[Claude Code](docs/connecting.md#claude-code)** — one registration command.
- **[Codex](docs/connecting.md#codex)** — one registration command.
- **[Cursor](docs/connecting.md#cursor)** — project MCP configuration.
- **[ChatGPT](docs/connecting.md#chatgpt)** — not directly supported by this local-only release; requires a reachable remote connection that is not included yet.

**Connecting tools and enabling automatic recording are two separate steps.** After connecting, load the bundled instructions, then complete the fictional first-use check in the guide. Setup examples are documented; live model behavior in these apps remains unverified.

## Download

Repository: https://github.com/MattChenyuanZhang/people-memory

Download a preview from [Releases](https://github.com/MattChenyuanZhang/people-memory/releases), or clone:

```sh
git clone https://github.com/MattChenyuanZhang/people-memory.git
cd people-memory
```

The Python package and CLI currently retain their original names: `people-match-memory` and `people-match`. This repository is called People Memory. The package is not published on PyPI; install from this checkout or the release wheel.

## Install

Requires Python 3.10+ with SQLite FTS5. Download this repository, open a terminal in it, and run:

```sh
python3 -m venv .venv
# macOS / Linux
.venv/bin/python -m pip install '.[mcp]'
.venv/bin/people-match init
```

On Windows use `.venv\Scripts\python.exe` and `.venv\Scripts\people-match.exe`.

The database is created outside the repository:

- macOS: `~/Library/Application Support/People Match/memory.sqlite3`
- Windows: `%LOCALAPPDATA%\People Match\memory.sqlite3`
- Linux: `$XDG_DATA_HOME/people-match/memory.sqlite3` or `~/.local/share/people-match/memory.sqlite3`

Set `PEOPLE_MATCH_DB` to an absolute path to use a different database. Point all assistants at the same file to share memory. Back up before changing versions. This release creates schema version 1, rejects newer databases and refuses to overwrite the original prototype schema.

## Connect your assistant

See [connection instructions](docs/connecting.md). A client launches:

```sh
/ABSOLUTE/PATH/TO/.venv/bin/people-match serve
```

This is a local stdio MCP process: it waits for client requests and does not open a network port. Simply starting it in a terminal is not an interactive chat.

Load [the people-memory skill](skills/people-memory/SKILL.md) or paste the output of `people-match instructions` into the assistant's persistent instructions. The MCP server also supplies the same instructions. Some hosts don't automatically apply all server instructions; verify with the fictional example before using real data.

## Everyday use

Say: “I met Riley today. Riley needs a PCB designer.” Supply a screenshot, pasted conversation, or note as evidence. The host assistant interprets attachments and calls recording tools with text. It should confirm what was saved and provide a change ID.

Ask: “Who needs hardware help?” or “What did Riley and I discuss?” No recall command is needed.

Say: “Riley found someone” to update the existing need. “Pause automatic recording,” “Don't save this,” and “Undo that save” are supported through the instructions and tools. `/record` is an optional explicit save request; an explicit request can save while automatic recording is paused. Don't-save exclusions still take precedence.

**Automatic capture depends on the assistant choosing to call the tools.** The server doesn't watch your messages, parse screenshots, or infer whether a statement is real. It enforces pause for automatic writes, evidence excerpts, identity collisions, atomic writes, and revision checks. An assistant can still misclassify content or tool parameters. Excluded content must never be sent to the server, including in source text. Retrieved text is untrusted data, not instructions.

Matching happens in your assistant. Search returns source-backed candidates using full-text OR terms; the assistant expands synonyms and checks each person's current history. Historical messages may mention resolved needs, so their text alone isn't an active match. There is no embedding service or proprietary matching model.

## Try the CLI with fictional data

```sh
.venv/bin/people-match record examples/record-riley.json
.venv/bin/people-match search 'PCB hardware' --category need --active
.venv/bin/people-match people Riley
.venv/bin/people-match changes
.venv/bin/people-match recording off
.venv/bin/people-match recording on
.venv/bin/people-match export /path/to/new-export.json
.venv/bin/people-match backup /path/to/new-backup.sqlite3
```

Use a person's returned ID with `person ID`. Use `undo CHANGE_ID` to undo an identified write. Undo refuses later-edit conflicts rather than overwriting history. To update an observation, retrieve its revision and use `update payload.json`; see [record formats](docs/data-format.md).

## Import the original prototype

This is explicit and read-only on the source. Use a **new, empty destination**:

```sh
.venv/bin/people-match --db /path/to/new-memory.sqlite3 import-legacy '/path/to/original/people_match.sqlite3'
```

Imports original people, confirmed account URLs, messages, extracted records, skill labels, and provenance metadata. Re-running identical content is idempotent. Original screenshots and files are not copied; source text and legacy references are preserved. Copy any desired attachments separately into storage you control. Cross-person original conversations are duplicated under participants for historical recall; forgetting one participant cannot erase what remains in another participant's conversation history.

## Privacy, undo, and deletion

Data is local, but content returned to a cloud assistant is sent to that assistant/provider. SQLite storage isn't encrypted by this package. Database, backup, and export files use restrictive permissions on supported systems. Your AI host controls tool approvals and can require confirmation for writes.

`forget PERSON_ID --confirm` permanently deletes the selected person's owned live records and related undo snapshots. Explain/confirm scope before using it. External exports, backups, other participants' histories, source platforms, and chat history are unaffected. This isn't forensic secure erasure. Undo is unavailable for deletion.

Export includes live records only. Backup preserves the complete SQLite database including history. An export cannot currently be restored by a dedicated command; restore a backup by pointing `PEOPLE_MATCH_DB` to a copied backup file with all clients stopped.

## Tests and release

```sh
.venv/bin/python -m unittest discover -s tests -v
```

CI runs unit and real stdio MCP integration tests across macOS, Windows, and Linux, then builds wheel/source archives. Only local macOS has been exercised in this development session; CI results will be available after you push. No GitHub repository or public release has been created by this package.

No API key is needed by People Match. Your assistant's subscription or usage charges still apply. Contributions should include tests for storage/identity/undo changes. See [architecture](docs/architecture.md).

Uninstall by disconnecting the MCP server and removing the installed environment. Personal databases remain until you deliberately remove them.

## License

[MIT](LICENSE).
