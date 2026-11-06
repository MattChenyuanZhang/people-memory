"""Transactional, versioned storage. No model calls and no network access."""
from __future__ import annotations
import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class MemoryError(ValueError):
    """Actionable validation or conflict error."""


def uid():
    return uuid.uuid4().hex


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def default_path():
    if os.environ.get("PEOPLE_MATCH_DB"):
        return Path(os.environ["PEOPLE_MATCH_DB"]).expanduser()
    if sys.platform == "darwin":
        return Path.home()/"Library/Application Support/People Match/memory.sqlite3"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home()))/"People Match/memory.sqlite3"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home()/".local/share"))/"people-match/memory.sqlite3"


def canonical_url(value):
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username:
        raise MemoryError("Account URL must be an http(s) URL without credentials")
    host = parts.hostname.lower().removeprefix("www.")
    if parts.port:
        host += ":" + str(parts.port)
    path = parts.path.rstrip("/")
    query, fragment = parts.query, parts.fragment
    if host in ("linkedin.com", "x.com", "twitter.com"):
        query = urlencode([(k,v) for k,v in parse_qsl(query, keep_blank_values=True)
                           if k.lower() != "trk" and not k.lower().startswith("utm_")])
        host = "x.com" if host == "twitter.com" else host
        path = path.lower()
    return urlunsplit(("https", host, path, query, fragment))


def iso_day(value):
    if value is not None:
        date.fromisoformat(value)
    return value


class Memory:
    def __init__(self, path=None):
        self.path = Path(path or default_path()).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=20000")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            self.db.close()
            raise MemoryError("Database is newer than this package; upgrade People Match")
        if version == 0:
            existing = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if existing and self.db.execute("PRAGMA user_version").fetchone()[0] != 1:
                self.db.close()
                raise MemoryError("Existing legacy database: use import-legacy into a NEW database")
        self.db.executescript('''
        BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS entities (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, person_id TEXT, data TEXT NOT NULL,
          revision INTEGER NOT NULL, deleted INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS changes (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, description TEXT NOT NULL,
          request_id TEXT UNIQUE, request_hash TEXT, undone INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS mutations (
          change_id TEXT NOT NULL REFERENCES changes(id), entity_id TEXT NOT NULL,
          before_data TEXT, before_deleted INTEGER, after_revision INTEGER NOT NULL,
          PRIMARY KEY(change_id,entity_id));
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT OR IGNORE INTO settings VALUES ('automatic_recording','true');
        CREATE INDEX IF NOT EXISTS entities_owner ON entities(person_id,kind,deleted);
        CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(entity_id UNINDEXED, text, tokenize='unicode61');
        CREATE TRIGGER IF NOT EXISTS entities_insert AFTER INSERT ON entities WHEN new.deleted=0 BEGIN
          INSERT INTO search_index(entity_id,text) VALUES(new.id,new.data);
        END;
        CREATE TRIGGER IF NOT EXISTS entities_update AFTER UPDATE ON entities BEGIN
          DELETE FROM search_index WHERE entity_id=old.id;
          INSERT INTO search_index(entity_id,text) SELECT new.id,new.data WHERE new.deleted=0;
        END;
        PRAGMA user_version=1;
        COMMIT;
        ''')
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _row(self, entity_id, include_deleted=False):
        r = self.db.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone()
        if not r or (r["deleted"] and not include_deleted):
            raise MemoryError("Record not found: " + entity_id)
        return r

    @staticmethod
    def unpack(r):
        return {"id": r["id"], "kind": r["kind"], "person_id": r["person_id"],
                "revision": r["revision"], "data": json.loads(r["data"])}

    def _change(self, description, request_id=None, request_hash=None):
        change_id = uid()
        self.db.execute(
                        "INSERT INTO changes(id,created_at,description,request_id,request_hash) VALUES (?,?,?,?,?)",
                        (change_id, datetime.now(timezone.utc).isoformat(), description, request_id, request_hash))
        return change_id

    def _put(self, change, kind, person_id, data, entity_id=None, expected_revision=None, deleted=0):
        entity_id = entity_id or uid()
        old = self.db.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone()
        if expected_revision is not None and (not old or old["revision"] != expected_revision):
            raise MemoryError("Record changed; retrieve it again before updating")
        if old and (old["kind"] != kind or old["person_id"] != person_id):
            raise MemoryError("Cannot change record identity or owner")
        revision = old["revision"] + 1 if old else 1
        self.db.execute("INSERT INTO mutations VALUES (?,?,?,?,?)", (change,entity_id,old["data"] if old else None,old["deleted"] if old else None,revision))
        self.db.execute("INSERT INTO entities VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,revision=excluded.revision,deleted=excluded.deleted",
                        (entity_id,kind,person_id,encode(data),revision,deleted))
        return entity_id

    def preferences(self):
        return {"automatic_recording": self.db.execute("SELECT value FROM settings WHERE key='automatic_recording'").fetchone()[0] == "true"}

    def set_recording(self, enabled):
        if type(enabled) is not bool:
            raise MemoryError("enabled must be boolean")
        with self.transaction():
            self.db.execute("UPDATE settings SET value=? WHERE key='automatic_recording'", ("true" if enabled else "false",))
        return self.preferences()

    def find_people(self, query="", account_url=None):
        target = canonical_url(account_url) if account_url else None
        found = []
        for r in self.db.execute("SELECT * FROM entities WHERE kind='person' AND deleted=0"):
            d = json.loads(r["data"])
            if target:
                match = target in d["accounts"]
            else:
                match = query.casefold() in (d["name"] + " " + " ".join(d.get("aliases", []))).casefold()
            if match:
                found.append(self.unpack(r))
        return found

    def _person(self, name, person_id, accounts, distinct):
        if person_id:
            r = self._row(person_id)
            if r["kind"] != "person":
                raise MemoryError("person_id is not a person")
            data = json.loads(r["data"])
            for account in accounts:
                matches = self.find_people(account_url=account)
                if matches and matches[0]["id"] != person_id:
                    raise MemoryError("Account belongs to another person")
            return person_id, data, False
        matches = {p["id"]:p for a in accounts for p in self.find_people(account_url=a)}
        if len(matches) > 1:
            raise MemoryError("Accounts identify different people; clarification required")
        if matches:
            p = next(iter(matches.values()))
            return p["id"], p["data"], False
        same_name = [p for p in self.find_people(name) if p["data"]["name"].casefold()==name.casefold()]
        if same_name and not distinct:
            raise MemoryError("Name already exists. Supply a confirmed person_id or confirm a distinct new person")
        return uid(), {"name":name,"aliases":[],"accounts":[]}, True

    def record(self, name, source_text, observations, person_id=None, account_urls=None,
               occurred_on=None, source_url=None, request_id=None, explicit=False,
               save_allowed=True, confirm_distinct=False):
        """Save one person and interaction atomically; observations are model-extracted."""
        if not isinstance(name,str) or not name.strip() or not isinstance(source_text,str) or not source_text.strip():
            raise MemoryError("Name and original source_text are required")
        if type(explicit) is not bool or type(save_allowed) is not bool or type(confirm_distinct) is not bool:
            raise MemoryError("Recording controls must be booleans")
        iso_day(occurred_on)
        if source_url:
            canonical_url(source_url)
        accounts = sorted(set(canonical_url(a) for a in (account_urls or [])))
        if not isinstance(observations,list) or len(observations)>200:
            raise MemoryError("observations must be a list with at most 200 entries")
        clean = []
        for item in observations:
            if not isinstance(item,dict):
                raise MemoryError("Each observation must be an object")
            category = item.get("category")
            text, evidence = item.get("text"), item.get("evidence")
            if category not in ("background","skill","interest","project","need","offer","commitment","note"):
                raise MemoryError("Invalid observation category")
            if not isinstance(text,str) or not text.strip() or not isinstance(evidence,str) or not evidence.strip() or evidence not in source_text:
                raise MemoryError("Each observation needs text and an exact evidence excerpt from source_text")
            certainty = item.get("certainty","explicit")
            status = item.get("status","open" if category in ("need","commitment") else "current")
            if certainty not in ("explicit","inferred","unverified") or status not in ("open","current","resolved","outdated","needs_confirmation"):
                raise MemoryError("Invalid certainty or status")
            observation = {"category":category,"text":text.strip(),"evidence":evidence,"certainty":certainty,"status":status}
            if "origin" in item:
                if category != "need" or item["origin"] not in ("requested", "user_created", "inferred"):
                    raise MemoryError("Need origin must be requested, user_created, or inferred, and applies only to needs")
                observation["origin"] = item["origin"]
            clean.append(observation)
        payload = dict(name=name.strip(),source_text=source_text,observations=clean,person_id=person_id,accounts=accounts,occurred_on=occurred_on,source_url=source_url,confirm_distinct=confirm_distinct)
        fingerprint = hashlib.sha256(encode(payload).encode()).hexdigest()
        key = request_id or "auto:"+fingerprint
        with self.transaction():
            if not save_allowed:
                raise MemoryError("Saving excluded by user")
            if not explicit and not self.preferences()["automatic_recording"]:
                raise MemoryError("Automatic recording is paused; explicit recording is still available")
            previous = self.db.execute("SELECT * FROM changes WHERE request_id=?", (key,)).fetchone()
            if previous:
                if previous["request_hash"] != fingerprint:
                    raise MemoryError("Request ID reused with different content")
                return {"saved":False,"duplicate":True,"change_id":previous["id"],"undone":bool(previous["undone"])}
            pid, data, new = self._person(name.strip(),person_id,accounts,confirm_distinct)
            change = self._change("Record interaction",key,fingerprint)
            updated = {**data,"accounts":sorted(set(data["accounts"]+accounts))}
            if new or updated != data:
                self._put(change,"person",None,updated,pid)
            interaction = self._put(change,"interaction",pid,{"source_text":source_text,"source_url":source_url,"occurred_on":occurred_on,"recorded_at":datetime.now(timezone.utc).isoformat()})
            ids=[]
            for item in clean:
                ids.append(self._put(change,"observation",pid,{**item,"interaction_id":interaction,"observed_on":occurred_on,"last_confirmed_on":occurred_on}))
            return {"saved":True,"change_id":change,"person_id":pid,"interaction_id":interaction,"observation_ids":ids}

    def person(self, person_id):
        person=self._row(person_id)
        if person["kind"]!="person":
            raise MemoryError("Not a person")
        return {"person":self.unpack(person),"records":[self.unpack(r) for r in self.db.execute("SELECT * FROM entities WHERE person_id=? AND deleted=0 ORDER BY rowid",(person_id,))]}

    def search(self, query, category=None, active_only=False, limit=30):
        if category and category not in ("background","skill","interest","project","need","offer","commitment","note"):
            raise MemoryError("Invalid category")
        if not 1 <= limit <= 100:
            raise MemoryError("limit must be 1..100")
        tokens = re.findall(r"\w+",query,flags=re.UNICODE)[:30]
        if not tokens:
            return []
        expression=" OR ".join('"'+t+'"' for t in tokens)
        candidates=self.db.execute("SELECT e.*,bm25(search_index) AS rank FROM search_index JOIN entities e ON e.id=search_index.entity_id WHERE search_index MATCH ? AND e.deleted=0 ORDER BY rank",(expression,))
        result=[]
        for r in candidates:
            item=self.unpack(r);d=item["data"]
            if category and d.get("category")!=category:
                continue
            if active_only and d.get("status") in ("resolved","outdated"):
                continue
            if item["person_id"]:
                item["person_name"]=json.loads(self._row(item["person_id"])["data"])["name"]
            result.append(item)
            if len(result)>=limit:
                break
        return result

    def update(self, observation_id, expected_revision, text, status, evidence, source_text, occurred_on=None, explicit=False, save_allowed=True):
        iso_day(occurred_on)
        if not isinstance(text,str) or not text.strip() or not isinstance(evidence,str) or not evidence.strip() or evidence not in source_text:
            raise MemoryError("Text and an exact evidence excerpt from source_text are required")
        if status not in ("open","current","resolved","outdated","needs_confirmation"):
            raise MemoryError("Invalid status")
        with self.transaction():
            if not save_allowed or (not explicit and not self.preferences()["automatic_recording"]):
                raise MemoryError("Recording excluded or paused")
            old=self._row(observation_id)
            if old["kind"]!="observation":
                raise MemoryError("Only observations can be updated")
            if old["revision"]!=expected_revision:
                raise MemoryError("Record changed; retrieve it again before updating")
            change=self._change("Update observation")
            interaction=self._put(change,"interaction",old["person_id"],{"source_text":source_text,"source_url":None,"occurred_on":occurred_on,"recorded_at":datetime.now(timezone.utc).isoformat()})
            data={**json.loads(old["data"]),"text":text.strip(),"status":status,"evidence":evidence,"interaction_id":interaction,"last_confirmed_on":occurred_on}
            self._put(change,"observation",old["person_id"],data,observation_id,expected_revision)
            return {"saved":True,"change_id":change,"observation_id":observation_id,"revision":expected_revision+1}

    def changes(self, limit=20):
        result=[]
        for r in self.db.execute("SELECT id,created_at,description,undone FROM changes ORDER BY rowid DESC LIMIT ?",(min(max(limit,1),100),)):
            entry=dict(r)
            entry["affected_records"]=[self.unpack(x) for x in self.db.execute(
                "SELECT e.* FROM entities e JOIN mutations m ON m.entity_id=e.id WHERE m.change_id=? AND e.deleted=0",(r["id"],))]
            result.append(entry)
        return result

    def undo(self, change_id):
        with self.transaction():
            change=self.db.execute("SELECT * FROM changes WHERE id=?",(change_id,)).fetchone()
            if not change or change["undone"]:
                raise MemoryError("Change not found or already undone")
            mutations=self.db.execute("SELECT * FROM mutations WHERE change_id=?",(change_id,)).fetchall()
            for m in mutations:
                current=self._row(m["entity_id"],True)
                if current["revision"]!=m["after_revision"]:
                    raise MemoryError("Cannot undo: record has later edits")
                if current["kind"]=="person" and m["before_data"] is None:
                    outside=self.db.execute("SELECT id FROM entities WHERE person_id=? AND deleted=0 AND id NOT IN (SELECT entity_id FROM mutations WHERE change_id=?)",(current["id"],change_id)).fetchone()
                    if outside:
                        raise MemoryError("Cannot undo person creation: later interactions depend on it")
            for m in mutations:
                self.db.execute("UPDATE entities SET data=?,deleted=?,revision=revision+1 WHERE id=?",(m["before_data"] or "{}",m["before_deleted"] if m["before_data"] is not None else 1,m["entity_id"]))
            self.db.execute("UPDATE changes SET undone=1 WHERE id=?",(change_id,))
            return {"undone":True,"change_id":change_id}

    def forget(self, person_id, confirm=False):
        if confirm is not True:
            raise MemoryError("Requires explicit user confirmation: permanently remove person, records, and related undo history. Backups are separate.")
        with self.transaction():
            p=self._row(person_id)
            if p["kind"]!="person":
                raise MemoryError("Not a person")
            ids=[r[0] for r in self.db.execute("SELECT id FROM entities WHERE id=? OR person_id=?",(person_id,person_id))]
            for eid in ids:
                # Redact old snapshots too, including tombstoned interactions.
                self.db.execute("DELETE FROM mutations WHERE entity_id=?",(eid,))
                self.db.execute("DELETE FROM search_index WHERE entity_id=?",(eid,))
                self.db.execute("DELETE FROM entities WHERE id=?",(eid,))
            self.db.execute("DELETE FROM changes WHERE id NOT IN (SELECT change_id FROM mutations)")
            return {"forgotten":True,"records_removed":len(ids),"scope":"Live database and related undo snapshots; external copies/backups unchanged. SQLite file may retain forensic remnants."}

    def export(self):
        return {"format":"people-match-1","automatic_recording":self.preferences()["automatic_recording"],"records":[self.unpack(r) for r in self.db.execute("SELECT * FROM entities WHERE deleted=0 ORDER BY rowid")]}

    def backup(self, destination):
        dest=Path(destination).expanduser()
        if dest.resolve()==self.path or dest.exists():
            raise MemoryError("Choose a new backup filename")
        dest.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        out=sqlite3.connect(dest)
        try:
            self.db.backup(out)
        finally:
            out.close()
        return {"backup":str(dest)}
