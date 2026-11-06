# Reference and maintenance

[Back to README](../README.md)

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

Use a person's returned ID with `person ID`. Use `undo CHANGE_ID` to undo an identified write. Undo refuses later-edit conflicts rather than overwriting history. To update an observation, retrieve its revision and use `update payload.json`; see [record formats](data-format.md).

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

All 17 tests and package builds passed across macOS, Windows, and Linux with Python 3.10 and 3.12. See the [verified run](https://github.com/MattChenyuanZhang/people-memory/actions/runs/42135951604) and [public developer-preview release](https://github.com/MattChenyuanZhang/people-memory/releases/tag/v0.1.0). Actual AI-app conversation behavior still needs validation.

No API key is needed by People Match. Your assistant's subscription or usage charges still apply. Contributions should include tests for storage/identity/undo changes. See [architecture](architecture.md).

Uninstall by disconnecting the MCP server and removing the installed environment. Personal databases remain until you deliberately remove them.

## Database location

The database is created outside the repository:

- macOS: `~/Library/Application Support/People Match/memory.sqlite3`
- Windows: `%LOCALAPPDATA%\People Match\memory.sqlite3`
- Linux: `$XDG_DATA_HOME/people-match/memory.sqlite3` or `~/.local/share/people-match/memory.sqlite3`

Set `PEOPLE_MATCH_DB` to an absolute path to use a different database. Point all assistants at the same file to share memory. Back up before changing versions. This release creates schema version 1, rejects newer databases and refuses to overwrite the original prototype schema.
