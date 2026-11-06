# Connect People Match to your AI app

People Match runs on your computer. Your AI app starts it and uses its tools to save or search your personal database. Downloading the repository alone does not connect anything.

**Setup status:** the local server works with real MCP SDK clients. The app-specific recipes below follow official documentation, but have not yet been validated in live AI-app conversations. ChatGPT needs a remote connection not shipped in this release.

## 1. Install once

Download/extract the source and open a terminal in the `people-match` folder.

macOS / Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[mcp]'
.venv/bin/people-match init
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[mcp]"
.\.venv\Scripts\people-match.exe init
```

Keep the installation folder in a permanent location: moving/deleting it later breaks the configured launch path.

Get your absolute launch path from the installation folder:

```sh
# macOS / Linux
.venv/bin/python -c 'from pathlib import Path; print(Path(".venv/bin/people-match").resolve())'
```

```powershell
# Windows PowerShell
(Resolve-Path .\.venv\Scripts\people-match.exe).Path
```

Replace `ABSOLUTE_LAUNCH_PATH` below with that result. Quote it when entering commands; JSON backslashes on Windows must be doubled. Do not paste placeholders unchanged.

Use the same personal database for all apps. Leaving `PEOPLE_MATCH_DB` unset uses the same default location for the same operating-system account. If you use a custom path, set the identical absolute `PEOPLE_MATCH_DB` value in each client's environment configuration. Don't point a new installation at the original prototype database; see the README's explicit import procedure.

## 2. Choose your app

### Claude Desktop

Open **Settings → Developer → Edit Config** when available. Alternatively, open the configuration file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add this server entry under `mcpServers`; preserve other existing entries and settings:

```json
{
  "mcpServers": {
    "people-match": {
      "command": "ABSOLUTE_LAUNCH_PATH",
      "args": ["serve"]
    }
  }
}
```

Restart Claude Desktop and check that People Match tools appear. Configuration file locations and launch format follow the [official MCP host guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/).

### Claude Code

With Claude Code installed, register the local server:

```sh
claude mcp add --scope user --transport stdio people-match -- "ABSOLUTE_LAUNCH_PATH" serve
```

For PowerShell the same command works with your quoted Windows launch path. Open a new Claude Code session and use `/mcp` to inspect the connection. User scope makes the connection available beyond the current project. To share project setup instead, use project scope and ensure paths work for each user; don't commit your personal absolute paths as a universal configuration.

To remove this user-scoped registration:

```sh
claude mcp remove --scope user people-match
```

Reference: [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp). This guide's registration syntax was also checked against locally installed CLI help; no user configuration was changed during documentation work.

### Codex

With the Codex CLI installed:

```sh
codex mcp add people-match -- "ABSOLUTE_LAUNCH_PATH" serve
codex mcp list
```

Open a new Codex session and verify that the tools are available. If the app doesn't show the new registration, check its MCP settings and selected profile. App/workspace configuration can affect visibility.

To remove the registration:

```sh
codex mcp remove people-match
```

Reference: [official OpenAI MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli). The add syntax was also checked against local CLI help. Codex configuration does not connect ordinary ChatGPT chats automatically.

### Cursor

In the project where you want People Match available, add the same JSON entry shown for Claude Desktop to `.cursor/mcp.json`. Preserve other servers. Open Cursor's MCP settings and enable/approve the server as needed.

This is project-scoped setup. Other projects need their own configuration or a user-level setup supported by your Cursor version. Reference: [official MCP host guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/).

### ChatGPT

**This release cannot connect directly to ordinary ChatGPT through a local launch command.** It exposes stdio, not an authenticated remote MCP endpoint.

A future ChatGPT path needs a connection reachable by ChatGPT: a supported secure local bridge or an authenticated hosted MCP service. Account/workspace access to custom MCP tools also matters. That connection and remote hosting are not implemented here. Don't paste a GitHub repository URL or a localhost URL into ChatGPT expecting it to run this package.

For now, use a local MCP client above, or use the CLI through a shell-capable agent. See [OpenAI's custom MCP guide](https://developers.openai.com/api/docs/guides/custom-mcp-server) for the remote integration model.

## 3. Enable the recording behavior

`people-match init` automatically installs the bundled `people-memory` and `record` skills for detected Codex and Claude Code installations. The Record skill makes the recording workflow selectable in apps that expose skills in their command menu. Restart or refresh the app if necessary. MCP registration and any app approval are still required.

If you installed the app later, rerun `people-match init`, or run `people-match install-skills --app codex` (use `--app claude-code` for Claude Code). Existing different skills are preserved and reported as skipped. `init --no-skills` skips installation. Other apps can use the portable skills when supported or load the instructions manually; MCP alone cannot add menu entries to every app.

Codex uses an existing `$CODEX_HOME/skills` or `~/.codex/skills` directory, otherwise `~/.agents/skills`. Claude Code uses `$CLAUDE_CONFIG_DIR/skills` or `~/.claude/skills`.

For an app without an installed memory skill, display the bundled instructions:

```sh
# macOS / Linux
.venv/bin/people-match instructions
```

```powershell
# Windows PowerShell
.\.venv\Scripts\people-match.exe instructions
```

Paste that output into the relevant assistant project's persistent instructions. In coding agents, it can be added to their project guidance file while preserving existing guidance. The portable skill is also available at [`skills/people-memory/SKILL.md`](../skills/people-memory/SKILL.md) for clients supporting agent skills.

The MCP server supplies these instructions too, but client handling varies. Installing a skill or configuring one project does not guarantee behavior in every other project/chat. Confirm it in each environment you plan to use.

## 4. Check it with fictional information

1. Ask: “Use People Match to show whether automatic recording is enabled.” Expect a `memory_preferences` tool result.
2. Send the following raw context (explicitly saving fictional test data is allowed):

   ```text
   /record
   This is fictional test data; please save it to test the connection.
   Riley Example: I need a PCB designer for a prototype.
   Me: I’ll ask around this week.
   ```

   Expect the assistant to extract Riley’s need and your follow-up without asking you to fill in fields, invoke the save tool, and return a successful change ID. Also try sharing readable context first and sending `/record` separately. For screenshots/files, check that your app can read the attachment; extraction is performed by your assistant, not the database.
3. In a fresh chat, ask: “Search People Match: what does Riley Example need?” Expect the need and its source evidence.
4. In a second app pointing to the same database, repeat the question. It should find the same person.
5. Say “Pause automatic recording.” Confirm the second app sees the paused preference.
6. Ask a hypothetical question and supply a detail with “don't save this.” Confirm no write occurs and excluded text is not passed into tools.
7. Resume recording. Say Riley found a designer; verify the existing need is resolved and excluded from active recommendations.
8. When testing automatic recording on real interactions, share one clear allowed statement without `/record`; check that the assistant actually invokes the recording tool and confirms success.

The automated suite tests cross-client storage at the protocol level; these steps test model behavior and application setup.

## Troubleshooting

- **No tools:** confirm installation with `[mcp]`, replace the path placeholder, and restart/reconnect the client.
- **Server appears to hang in a terminal:** `serve` waits for MCP requests. This is expected; launch it through the AI app.
- **Tools available but nothing saves:** check `memory_preferences`, load the instructions, inspect host write approvals, and explicitly ask for a save to distinguish tool connectivity from automatic behavior.
- **Second app finds no data:** verify both apps run under the same operating-system account and use the same `PEOPLE_MATCH_DB` or default path.
- **Moved installation:** update the absolute launch path in the client configuration.
- **Ambiguous person:** supply a confirmed account URL or clarify the existing person. Don't force duplicate creation to bypass identity checks.
- **Uninstall:** remove the client registration. Personal databases remain until deliberately deleted.

Your data is local, but records returned to a cloud model are processed by that provider. Host tool approval settings still apply. Never publish your personal database with your GitHub repository.
