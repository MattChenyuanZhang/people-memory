"""Portable local CLI; JSON in, JSON out."""
import argparse
import json
import os
import sqlite3
import sys
from importlib.resources import files
from pathlib import Path
from .core import Memory, MemoryError, default_path


def main():
    p=argparse.ArgumentParser(description="People Match: persistent relationship memory")
    p.add_argument("--db",help="Database path (or PEOPLE_MATCH_DB); defaults outside the source repository")
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("init");a.add_argument("--no-skills",action="store_true",help="Skip automatic skill installation")
    a=sub.add_parser("install-skills",help="Install bundled skills for a supported AI app")
    a.add_argument("--app",choices=["auto","codex","claude-code"],default="auto")
    sub.add_parser("serve",help="Start local stdio MCP server")
    sub.add_parser("instructions",help="Print assistant instructions")
    a=sub.add_parser("record");a.add_argument("file",help="JSON payload path; - reads stdin")
    a=sub.add_parser("search");a.add_argument("query");a.add_argument("--category");a.add_argument("--active",action="store_true")
    a=sub.add_parser("people");a.add_argument("query",nargs="?",default="");a.add_argument("--account-url")
    a=sub.add_parser("person");a.add_argument("person_id")
    a=sub.add_parser("update");a.add_argument("file",help="JSON update payload; - reads stdin")
    a=sub.add_parser("recording");a.add_argument("state",choices=["on","off","status"])
    sub.add_parser("changes")
    a=sub.add_parser("undo");a.add_argument("change_id")
    a=sub.add_parser("forget");a.add_argument("person_id");a.add_argument("--confirm",action="store_true")
    a=sub.add_parser("export");a.add_argument("output")
    a=sub.add_parser("backup");a.add_argument("output")
    a=sub.add_parser("import-legacy");a.add_argument("source",help="Read-only version-1 People Match database")
    args=p.parse_args()
    if args.db:
        os.environ["PEOPLE_MATCH_DB"]=str(Path(args.db).expanduser().resolve())
    if args.command=="install-skills":
        from .setup_skills import install_skills
        print(json.dumps(install_skills(args.app),ensure_ascii=False,indent=2));return
    if args.command=="instructions":
        print(files("people_match").joinpath("instructions.md").read_text());return
    if args.command=="serve":
        try:
            from .server import main as serve
        except ImportError:
            p.error('MCP dependency missing. Install this package with the [mcp] extra.')
        serve();return
    memory=None
    try:
        memory=Memory()
        cmd=args.command
        if cmd=="init":
            result={"database":str(memory.path),**memory.preferences()}
            if not args.no_skills:
                from .setup_skills import install_skills
                result.update(install_skills())
        elif cmd in ("record","update"):
            payload=json.load(sys.stdin) if args.file=="-" else json.loads(Path(args.file).read_text())
            result=getattr(memory,cmd)(**payload)
        elif cmd=="search":result=memory.search(args.query,args.category,args.active)
        elif cmd=="people":result=memory.find_people(args.query,args.account_url)
        elif cmd=="person":result=memory.person(args.person_id)
        elif cmd=="recording":result=memory.preferences() if args.state=="status" else memory.set_recording(args.state=="on")
        elif cmd=="changes":result=memory.changes()
        elif cmd=="undo":result=memory.undo(args.change_id)
        elif cmd=="forget":result=memory.forget(args.person_id,args.confirm)
        elif cmd=="backup":result=memory.backup(args.output)
        elif cmd=="export":
            with open(args.output,"x",encoding="utf-8",opener=lambda path,flags:os.open(path,flags,0o600)) as f:
                json.dump(memory.export(),f,ensure_ascii=False,indent=2)
            result={"export":args.output,"scope":"Live records only, not undo history or external source files"}
        elif cmd=="import-legacy":
            from .legacy import import_legacy
            result=import_legacy(memory,args.source)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (MemoryError,ValueError,TypeError,OSError,sqlite3.Error) as exc:
        print(json.dumps({"error":str(exc)},ensure_ascii=False),file=sys.stderr);raise SystemExit(1)
    finally:
        if memory:
            memory.close()


if __name__=="__main__":
    main()
