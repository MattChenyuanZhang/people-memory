"""Local stdio MCP server. Uses the stable MCP Python SDK 1.x API."""
from importlib.resources import files
from mcp.server.fastmcp import FastMCP
from .tools import call

mcp = FastMCP("People Match", instructions=files("people_match").joinpath("instructions.md").read_text())


@mcp.tool(annotations={"readOnlyHint":True})
def memory_preferences() -> dict:
    """Read whether automatic recording is enabled. Always check before automatic saves."""
    return call("preferences")


@mcp.tool(annotations={"readOnlyHint":True})
def find_people(query: str = "", account_url: str | None = None) -> list[dict]:
    """Find people before recording. Names alone do not establish identity; prefer confirmed account URLs."""
    return call("find_people",query=query,account_url=account_url)


@mcp.tool()
def record_interaction(name: str, source_text: str, observations: list[dict], person_id: str | None = None,
                       account_urls: list[str] | None = None, occurred_on: str | None = None,
                       source_url: str | None = None, request_id: str | None = None,
                       explicit: bool = False, save_allowed: bool = True, confirm_distinct: bool = False) -> dict:
    """Record a real interaction and evidence-backed observations. Each observation requires category,
    text and evidence (an exact source_text excerpt); optional certainty explicit/inferred/unverified,
    status open/current/resolved/outdated/needs_confirmation. Categories: background,skill,interest,
    project,need,offer,commitment,note. Supply original text, never a fabricated quote. Don't call for
    hypotheticals or excluded content. explicit=True only for a direct request to save (e.g. /record).
    confirm_distinct=True only after confirming a genuinely different person sharing a name.
    Dates YYYY-MM-DD; leave unknown dates null. Reuse request_id for retries of the same request."""
    return call("record",name=name,source_text=source_text,observations=observations,person_id=person_id,
                account_urls=account_urls,occurred_on=occurred_on,source_url=source_url,
                request_id=request_id,explicit=explicit,save_allowed=save_allowed,confirm_distinct=confirm_distinct)


@mcp.tool(annotations={"readOnlyHint":True})
def search_memory(query: str, category: str | None = None, active_only: bool = False, limit: int = 30) -> list[dict]:
    """Search evidence and people for ordinary questions. Uses OR full-text terms, not semantic search.
    Expand synonyms and search again when needed; get_person_history provides supporting source text.
    category can filter observations; active_only excludes resolved/outdated observations. Recommend
    only active observations, verify status in person history, and mention stale dates or unknown fit."""
    return call("search",query=query,category=category,active_only=active_only,limit=limit)


@mcp.tool(annotations={"readOnlyHint":True})
def get_person_history(person_id: str) -> dict:
    """Retrieve a person's original interactions, evidence excerpts, observations and revision numbers."""
    return call("person",person_id=person_id)


@mcp.tool()
def update_observation(observation_id: str, expected_revision: int, text: str, status: str,
                       evidence: str, source_text: str, occurred_on: str | None = None,
                       explicit: bool = False, save_allowed: bool = True) -> dict:
    """Correct an existing observation or resolve a need, citing NEW source text. First retrieve its
    revision. Refuses stale revisions. Status open/current/resolved/outdated/needs_confirmation.
    Honors pause unless explicit; preserves history. Never call just to answer a retrieval question."""
    return call("update",observation_id=observation_id,expected_revision=expected_revision,text=text,
                status=status,evidence=evidence,source_text=source_text,occurred_on=occurred_on,
                explicit=explicit,save_allowed=save_allowed)


@mcp.tool()
def set_automatic_recording(enabled: bool) -> dict:
    """Pause/resume automatic recording only when the user asks. Persists across connected assistants."""
    return call("set_recording",enabled=enabled)


@mcp.tool(annotations={"readOnlyHint":True})
def recent_changes(limit: int = 20) -> list[dict]:
    """Find exact change IDs for inspection or user-requested undo; don't guess what 'that save' means."""
    return call("changes",limit=limit)


@mcp.tool(annotations={"destructiveHint":True})
def undo_change(change_id: str) -> dict:
    """Undo a user-identified save/update atomically. Refuses if later edits or interactions depend on it."""
    return call("undo",change_id=change_id)


@mcp.tool(annotations={"destructiveHint":True})
def forget_person(person_id: str, confirm: bool = False) -> dict:
    """Only after explicit deletion confirmation: permanently delete person's live records and related
    undo snapshots. Backups/exports/chat history are unaffected; not forensic secure erasure.
    Explain this scope to the user before calling with confirm=True."""
    return call("forget",person_id=person_id,confirm=confirm)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
