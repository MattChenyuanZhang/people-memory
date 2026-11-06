from pathlib import Path
import sqlite3
import tempfile
import unittest
from people_match.core import Memory
from people_match.legacy import import_legacy


class LegacyTests(unittest.TestCase):
    def test_source_untouched_and_need_survives_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"old.sqlite3"
            c=sqlite3.connect(source)
            c.executescript(Path(__file__).with_name('legacy_schema.sql').read_text())
            c.execute("INSERT INTO people(id,display_name) VALUES ('r','Riley')")
            c.execute("INSERT INTO sources(id,kind,title) VALUES ('s','note','Fictional source')")
            c.execute("INSERT INTO conversations VALUES ('c','test','Test','s')")
            c.execute("INSERT INTO participants VALUES ('c','r')")
            c.execute("INSERT INTO messages VALUES ('m','c','r',NULL,NULL,1,'Need PCB help','s')")
            c.execute("INSERT INTO needs(id,person_id,title,description,evidence_message_id,source_id) VALUES ('n','r','PCB','Need PCB help','m','s')")
            c.execute("INSERT INTO need_skills VALUES ('n','PCB design')")
            c.commit();c.close()
            before=source.read_bytes()
            m=Memory(Path(tmp)/'new.sqlite3')
            try:
                imported=import_legacy(m,source)
                self.assertTrue(imported['imported'])
                need=m.search('PCB',category='need',active_only=True)[0]
                p=m.person(need['person_id'])
                self.assertTrue(any(x['kind']=='interaction' for x in p['records']))
                self.assertEqual(p['person']['data']['name'],'Riley')
                self.assertTrue(import_legacy(m,source)['duplicate'])
                m.forget(p['person']['id'],True)
                self.assertEqual(m.export()['records'],[])
                self.assertEqual(source.read_bytes(),before)
            finally:m.close()


if __name__=='__main__':unittest.main()
