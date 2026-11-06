"""Install bundled skills into supported local hosts without replacing user files."""
from importlib.resources import files
from pathlib import Path
import os


def install_skills(app="auto", home=None):
    home = Path.home() if home is None else Path(home)
    codex = Path(os.environ.get("CODEX_HOME", home / ".codex"))
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude"))
    destinations = {
        "codex": codex / "skills" if "CODEX_HOME" in os.environ or (codex / "skills").is_dir() else home / ".agents" / "skills",
        "claude-code": claude / "skills",
    }
    detected = {"codex": codex.is_dir(), "claude-code": claude.is_dir()}
    selected = [name for name in destinations if app == name or (app == "auto" and detected[name])]
    results = []
    bundled = files("people_match").joinpath("bundled_skills")
    for host in selected:
        for name in ("people-memory", "record"):
            relative_paths = ["SKILL.md"]
            if name == "record":
                relative_paths.append("agents/openai.yaml")
            target = destinations[host] / name
            item = {"app": host, "skill": name, "path": str(target)}
            try:
                expected = {rel: bundled.joinpath(name, *rel.split("/")).read_bytes() for rel in relative_paths}
                paths = [destinations[host], target, target / "agents"]
                if any(path.is_symlink() for path in paths):
                    raise ValueError("Existing symlink preserved; install this skill manually")
                for rel, content in expected.items():
                    dest = target / rel
                    if dest.is_symlink() or (dest.exists() and (not dest.is_file() or dest.read_bytes() != content)):
                        raise ValueError("Existing custom skill preserved; review it before updating")
                added = False
                for rel, content in expected.items():
                    dest = target / rel
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with dest.open("xb") as output:
                            output.write(content)
                        added = True
                item["status"] = "installed" if added else "already_installed"
            except (OSError, ValueError) as exc:
                item.update(status="skipped", reason=str(exc))
            results.append(item)
    return {"skills": results, "note": "Restart or refresh your AI app if the skills do not appear. MCP must also be connected." if selected else "No supported local app detected. Run install-skills --app codex or --app claude-code after choosing your app, or load the bundled instructions manually."}
