import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from people_match.core import Memory, MemoryError


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"memory.sqlite3"
        self.m=Memory(self.path)

    def tearDown(self):
        self.m.close();self.tmp.cleanup()

    def record(self, **extra):
        payload=dict(name="Ben",source_text="Ben designs PCBs and likes startups.",observations=[{"category":"skill","text":"PCB design","evidence":"designs PCBs"}],account_urls=["https://www.linkedin.com/in/ben-example/?trk=abc"])
        payload.update(extra)
        return self.m.record(**payload)

    def test_record_retrieve_and_search_evidence(self):
        r=self.record();p=self.m.person(r["person_id"])
        self.assertEqual(len(p["records"]),2)
        self.assertEqual(p["person"]["data"]["accounts"],["https://linkedin.com/in/ben-example"])
        hits=self.m.search("PCB")
        self.assertEqual(hits[0]["data"]["evidence"],"designs PCBs")
        self.assertEqual(self.m.search('" OR 1=1; --'),[])
        self.assertEqual(self.m.person(r["person_id"]),p)

    def test_duplicate_and_retry_collision(self):
        a=self.record();b=self.record()
        self.assertTrue(b["duplicate"]);self.assertEqual(a["change_id"],b["change_id"])
        self.record(request_id="message-1")
        with self.assertRaises(MemoryError):self.record(request_id="message-1",source_text="Ben designs PCBs twice.")

    def test_ambiguous_name_not_merged(self):
        a=self.record(account_urls=[])
        with self.assertRaises(MemoryError):self.record(account_urls=[],source_text="Ben designs PCBs again.")
        b=self.record(account_urls=[],source_text="Ben designs PCBs again.",confirm_distinct=True)
        self.assertNotEqual(a["person_id"],b["person_id"])

    def test_accounts_resolve_and_conflict(self):
        a=self.record()
        b=self.record(name="Benjamin",source_text="Ben designs PCBs again.")
        self.assertEqual(a["person_id"],b["person_id"])
        c=self.record(name="Other",account_urls=["https://x.com/other"],source_text="Other designs PCBs")
        with self.assertRaises(MemoryError):self.record(person_id=c["person_id"])
        with self.assertRaises(MemoryError):self.record(account_urls=["https://linkedin.com/in/ben-example","https://x.com/other"])

    def test_identity_bearing_queries_and_fragments_are_not_merged(self):
        a=self.record(name="Alice",account_urls=["https://example.com/profile.php?id=alice"])
        b=self.record(name="Bob",account_urls=["https://example.com/profile.php?id=bob"])
        self.assertNotEqual(a["person_id"],b["person_id"])
        c=self.record(name="Carol",account_urls=["https://example.com/#/carol"])
        d=self.record(name="Dana",account_urls=["https://example.com/#/dana"])
        self.assertNotEqual(c["person_id"],d["person_id"])

    def test_pause_exclusion_and_explicit_override(self):
        self.m.set_recording(False)
        with self.assertRaises(MemoryError):self.record()
        with self.assertRaises(MemoryError):self.record(explicit=True,save_allowed=False)
        self.assertEqual(self.m.export()["records"],[])
        self.assertTrue(self.record(explicit=True)["saved"])
        other=Memory(self.path)
        try:self.assertFalse(other.preferences()["automatic_recording"])
        finally:other.close()

    def test_invalid_evidence_rolls_back(self):
        with self.assertRaises(MemoryError):self.record(observations=[{"category":"skill","text":"robotics","evidence":"invented"}])
        self.assertEqual(self.m.export()["records"],[])
        self.assertEqual(self.m.changes(),[])

    def test_resolved_need_and_version_conflict(self):
        a=self.record(observations=[{"category":"need","text":"PCB designer wanted","evidence":"PCBs"}])
        oid=a["observation_ids"][0]
        b=self.m.update(oid,1,"PCB designer found","resolved","found","Ben found a designer.")
        self.assertEqual(self.m.search("PCB",category="need",active_only=True),[])
        with self.assertRaises(MemoryError):self.m.update(oid,1,"changed","open","Ben","Ben changed.")
        self.m.undo(b["change_id"])
        self.assertTrue(self.m.search("PCB",category="need",active_only=True))
        with self.assertRaises(MemoryError):self.m.undo(a["change_id"])

    def test_undo_creation_and_duplicate_after_undo(self):
        a=self.record();self.m.undo(a["change_id"])
        self.assertEqual(self.m.export()["records"],[])
        self.assertTrue(self.record()["undone"])
        with self.assertRaises(MemoryError):self.m.undo(a["change_id"])

    def test_undo_preserves_later_interactions(self):
        a=self.record();self.record(person_id=a["person_id"],source_text="Ben designs PCBs for a new project.")
        with self.assertRaises(MemoryError):self.m.undo(a["change_id"])
        self.assertEqual(len(self.m.person(a["person_id"])["records"]),4)

    def test_forget_removes_undo_and_search(self):
        a=self.record()
        with self.assertRaises(MemoryError):self.m.forget(a["person_id"])
        self.m.forget(a["person_id"],True)
        self.assertEqual(self.m.export()["records"],[])
        self.assertEqual(self.m.changes(),[])
        self.assertEqual(self.m.search("PCB"),[])
        self.assertEqual(self.m.db.execute("SELECT COUNT(*) FROM mutations").fetchone()[0],0)

    def test_backup_and_permissions(self):
        self.record();dest=Path(self.tmp.name)/"backup.sqlite3";self.m.backup(dest)
        other=Memory(dest)
        try:self.assertEqual(other.export(),self.m.export())
        finally:other.close()
        with self.assertRaises(MemoryError):self.m.backup(dest)
        if os.name!="nt":self.assertEqual(self.path.stat().st_mode & 0o777,0o600)

    def test_cli_separate_process_retrieval(self):
        self.record()
        proc=subprocess.run([sys.executable,"-m","people_match.cli","--db",str(self.path),"search","PCB"],capture_output=True,text=True,check=True)
        self.assertTrue(json.loads(proc.stdout))

    def test_unknown_schema_is_not_modified(self):
        path=Path(self.tmp.name)/"future.sqlite3";db=sqlite3.connect(path);db.execute("PRAGMA user_version=99");db.close()
        with self.assertRaises(MemoryError):Memory(path)
        with sqlite3.connect(path) as db:self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0],99)

    def test_old_schema_requires_explicit_import(self):
        path=Path(self.tmp.name)/"legacy.sqlite3";db=sqlite3.connect(path);db.execute("CREATE TABLE people(id TEXT)");db.close()
        with self.assertRaises(MemoryError):Memory(path)


if __name__=="__main__":unittest.main()
