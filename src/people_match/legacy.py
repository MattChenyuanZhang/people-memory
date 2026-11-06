"""Explicit read-only import from the original prototype schema."""
import hashlib
import sqlite3
from pathlib import Path
from .core import MemoryError, encode


def import_legacy(memory, source):
    path=Path(source).expanduser().resolve()
    if path==memory.path:
        raise MemoryError("Import into a new database; source must differ from destination")
    legacy=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
    legacy.row_factory=sqlite3.Row
    try:
        required={"people","accounts","conversations","participants","messages","facts","needs","need_skills","offers","followups","sources"}
        names={r[0] for r in legacy.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= names:
            raise MemoryError("Not the supported original People Match database")
        tables={t:[dict(r) for r in legacy.execute('SELECT * FROM '+t)] for t in sorted(required)}
    finally:
        legacy.close()
    digest=hashlib.sha256(encode(tables).encode()).hexdigest()
    prefix="legacy-"+digest[:16]+"-"
    counts={}
    with memory.transaction():
        previous=memory.db.execute("SELECT id,undone FROM changes WHERE request_id=?",("legacy:"+digest,)).fetchone()
        if previous:
            return {"imported":False,"duplicate":True,"change_id":previous["id"],"undone":bool(previous["undone"])}
        # Fresh target avoids silent identity merges; reruns of identical content are idempotent.
        if memory.db.execute("SELECT 1 FROM entities WHERE deleted=0 LIMIT 1").fetchone():
            raise MemoryError("Legacy import requires an empty target; choose a new --db path")
        change=memory._change("Import legacy database","legacy:"+digest,digest)
        def put(kind,old_id,owner,data):
            eid=prefix+kind+"-"+str(old_id)
            memory._put(change,kind,prefix+"person-"+owner if owner else None,data,eid)
            counts[kind]=counts.get(kind,0)+1
            return eid
        from .core import canonical_url
        for p in tables["people"]:
            accounts=[]
            for a in tables["accounts"]:
                if a["person_id"]==p["id"] and a.get("url") and a.get("identity_status")=="confirmed":
                    accounts.append(canonical_url(a["url"]))
            put("person",p["id"],None,{"name":p["display_name"],"aliases":[],"accounts":accounts,"legacy":p})
        for person in tables["people"]:
            for source in tables["sources"]:
                referenced = any(x.get("source_id")==source["id"] and x.get("person_id")==person["id"] for table in ("facts","needs","offers") for x in tables[table])
                if referenced:
                    put("source",source["id"]+"-"+person["id"],person["id"],{**source,"local_file_copied":False})
        for msg in tables["messages"]:
            participants=[x["person_id"] for x in tables["participants"] if x["conversation_id"]==msg["conversation_id"]]
            for owner in participants:
                put("interaction",msg["id"]+"-"+owner,owner,{"source_text":msg["body"],"occurred_on":(msg.get("sent_at") or "")[:10] or None,"sender_id":prefix+"person-"+msg["sender_id"],"legacy":msg})
        for table,category in [("facts",None),("needs","need"),("offers","offer"),("followups","commitment")]:
            for item in tables[table]:
                owner=item["person_id"]
                body=item.get("statement") or item.get("description") or item.get("title") or ""
                msg=next((x for x in tables["messages"] if x["id"]==item.get("evidence_message_id")),None)
                iid=prefix+"interaction-"+msg["id"]+"-"+owner if msg else None
                mapped=item.get("status","current")
                mapped={"fulfilled":"resolved","closed":"resolved","done":"resolved","cancelled":"resolved"}.get(mapped,mapped)
                cat=category or (item.get("category") if item.get("category") in ("background","skill","interest","project","need","offer","commitment","note") else "background")
                put("observation",table+"-"+item["id"],owner,{"category":cat,"text":body,"certainty":item.get("certainty","explicit"),"status":mapped,"evidence":msg["body"] if msg else "Legacy source reference; inspect preserved source metadata", "interaction_id":iid,"last_confirmed_on":item.get("last_confirmed_on") or item.get("observed_on"),"legacy":item})
        # Keep ancillary rows to retain exact prototype provenance and skill labels.
        for p in tables["people"]:
            needs={x["id"] for x in tables["needs"] if x["person_id"]==p["id"]}
            put("legacy_metadata",p["id"],p["id"],{"need_skills":[x for x in tables["need_skills"] if x["need_id"] in needs],"accounts":[x for x in tables["accounts"] if x["person_id"]==p["id"]]})
        return {"imported":True,"change_id":change,"counts":counts,"source_modified":False,"source_files_copied":False}
