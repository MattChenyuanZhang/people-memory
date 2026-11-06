# People Memory

Relationship memory for your AI assistant. Remember what people need, what they can offer, and what you discussed—then use that context when something relevant comes up.

[How to use it](#how-to-use-it) · [Getting started](#getting-started)

## How to use it

Once installed and connected, use your normal AI chat.

### Record information about someone

**Use natural language:**

> “I met Alex today. Alex is building a hardware startup and needs someone with PCB design and embedded systems experience.”

Your assistant should identify Alex, save the relevant information and its source, and briefly confirm what it recorded. You can also paste a conversation, attach a screenshot, or include a profile link to identify the person. A profile link alone doesn't give access to private messages.

**Or explicitly start recording with `/record`:**

> “/record Here’s my conversation with Alex. Remember what Alex is looking for and anything I promised to follow up on.”

Provide the conversation with your message. If information is missing or the person's identity is ambiguous, the assistant should ask before saving. Check its confirmation rather than assuming a save happened.

Updates work the same way. For example: “Alex found someone for PCB design. That need is resolved.” Your assistant should update the existing record and confirm the change.

### Connect new information to what you already know

Later, you meet someone else:

> “I met Ben today. Ben designs PCBs, works with Raspberry Pi, and is interested in advising startups. Does this help anyone I’ve mentioned before?”

Your assistant searches the saved information and can connect Ben’s experience to Alex’s earlier request:

> **Example response:** “Alex previously asked for PCB design and embedded systems help. Ben may be a fit. We should check that Alex still needs help and that Ben is open to an introduction.”

The assistant uses your past interactions as evidence and explains the fit and any missing information. It doesn't contact either person automatically. Matching happens when the assistant searches and reasons over your records; it isn't a background scan of everything you do.

You can also ask directly:

> “Who could help Alex with hardware?”
>
> “What did Alex and I discuss last time?”
>
> “Have I promised anyone an introduction?”

No recall command is needed. Another connected AI app can use the same history if it points to the same database.

**Automatic recording depends on your assistant using the connected tools and instructions.** People Memory doesn't independently monitor every chat. Saved records stay on your computer; records returned to a cloud assistant are processed by that assistant's provider.

## Getting started

Complete these steps before using the chat workflows above.

### 1. Check the requirements

- Python 3.10 or newer, with SQLite FTS5 support.
- An AI app that supports **local MCP servers**—a way for the assistant to call tools on your computer.
- Access to that app's MCP settings and persistent assistant instructions.

People Memory doesn't need its own model API key. Your chosen assistant may require an account, subscription, or API access.

**Current release:** public developer preview, running locally. Direct ordinary ChatGPT connectivity isn't included; it needs a reachable remote connection. App-specific setup is documented, but live automatic-recording behavior still needs validation. See the [connection guide](docs/connecting.md) for examples and limitations.

### 2. Download

Download and extract the source ZIP from [Releases](https://github.com/MattChenyuanZhang/people-memory/releases), or clone:

```sh
git clone https://github.com/MattChenyuanZhang/people-memory.git
cd people-memory
```

Open a terminal in the extracted/cloned folder. Keep it in a permanent location so your app's connection path won't break later.

### 3. Install and create your database

**macOS / Linux:**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[mcp]'
.venv/bin/people-match init
```

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[mcp]"
.\.venv\Scripts\people-match.exe init
```

`init` creates your personal database outside the repository and prints its location. To share memory across AI apps, use that same database in each connection. Do not upload it to GitHub.

The package and command currently retain their original names, `people-match-memory` and `people-match`. The repository is called People Memory. Install from this download; the package isn't published on PyPI.

### 4. Connect your AI app

Follow the [connection guide](docs/connecting.md) for your app. Register a **local stdio MCP server** with:

- **Command:** the absolute path to `.venv/bin/people-match`, or `.venv\Scripts\people-match.exe` on Windows.
- **Arguments:** `serve`.

Your app starts this process when it needs the tools. You don't need to leave a manually launched server running in a terminal.

### 5. Load the memory instructions

Display the bundled instructions:

```sh
# macOS / Linux
.venv/bin/people-match instructions
```

```powershell
# Windows PowerShell
.\.venv\Scripts\people-match.exe instructions
```

Add the output to your assistant's persistent project instructions, preserving any instructions already there. If your app supports agent skills, you can install the included [people-memory skill](skills/people-memory/SKILL.md) instead. Check the connection guide for details.

**The connection provides the tools; the instructions explain when to record and retrieve.** Each app/project you use needs the appropriate setup.

### 6. Verify before using real information

In a new connected chat:

1. Ask: “Use People Memory to show whether automatic recording is enabled.”
2. Say: “Please explicitly save this fictional test person: Riley Example needs a PCB designer.” Check for a successful save confirmation and change ID.
3. In a fresh chat, ask: “Search my memory: what does Riley Example need?” Check that the saved need and evidence are retrieved.

Then follow the [full first-use check](docs/connecting.md#4-check-it-with-fictional-information) to test updates, pause, exclusions, and cross-app recall. You're ready to try the natural-language workflows above when these checks work in your app.

### Further details

- [Connection examples and troubleshooting](docs/connecting.md)
- [Backups, export, CLI commands, privacy, deletion, and prototype import](docs/reference.md)
- [Architecture](docs/architecture.md) and [record formats](docs/data-format.md)
- [Automated test results](https://github.com/MattChenyuanZhang/people-memory/actions/runs/42135951604): 17 tests and package builds passed on macOS, Windows, and Linux with Python 3.10 and 3.12. These test the software and MCP protocol, not actual model behavior.

[MIT license](LICENSE). Always free.
