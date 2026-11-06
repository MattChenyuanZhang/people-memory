PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE people(id TEXT PRIMARY KEY,display_name TEXT NOT NULL,relationship TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE accounts(id INTEGER PRIMARY KEY,person_id TEXT NOT NULL REFERENCES people(id),platform TEXT NOT NULL,account_key TEXT NOT NULL,url TEXT,identity_status TEXT NOT NULL DEFAULT 'confirmed' CHECK(identity_status IN ('confirmed','unconfirmed')),UNIQUE(platform,account_key));
CREATE TABLE sources(id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,url TEXT,local_path TEXT,captured_on TEXT,description TEXT);
CREATE TABLE conversations(id TEXT PRIMARY KEY,platform TEXT NOT NULL,title TEXT NOT NULL,source_id TEXT REFERENCES sources(id));
CREATE TABLE participants(conversation_id TEXT REFERENCES conversations(id),person_id TEXT REFERENCES people(id),PRIMARY KEY(conversation_id,person_id));
CREATE TABLE messages(id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES conversations(id),sender_id TEXT NOT NULL REFERENCES people(id),sent_at TEXT,time_basis TEXT,sequence INTEGER NOT NULL,body TEXT NOT NULL,source_id TEXT NOT NULL REFERENCES sources(id),UNIQUE(conversation_id,sequence));
CREATE TABLE facts(id TEXT PRIMARY KEY,person_id TEXT NOT NULL REFERENCES people(id),category TEXT NOT NULL,statement TEXT NOT NULL,evidence_message_id TEXT REFERENCES messages(id),source_id TEXT NOT NULL REFERENCES sources(id),certainty TEXT NOT NULL CHECK(certainty IN ('explicit','inferred','unverified')),observed_on TEXT,expires_on TEXT);
CREATE TABLE needs(id TEXT PRIMARY KEY,person_id TEXT NOT NULL REFERENCES people(id),title TEXT NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','needs_confirmation','fulfilled','closed')),urgency TEXT,deadline TEXT,first_observed_on TEXT,last_confirmed_on TEXT,evidence_message_id TEXT REFERENCES messages(id),source_id TEXT NOT NULL REFERENCES sources(id));
CREATE TABLE need_skills(need_id TEXT REFERENCES needs(id),skill TEXT NOT NULL,PRIMARY KEY(need_id,skill));
CREATE TABLE offers(id TEXT PRIMARY KEY,person_id TEXT NOT NULL REFERENCES people(id),skill TEXT NOT NULL,description TEXT,willingness TEXT NOT NULL DEFAULT 'unknown' CHECK(willingness IN ('unknown','open','unavailable')),source_id TEXT NOT NULL REFERENCES sources(id),evidence_message_id TEXT REFERENCES messages(id));
CREATE TABLE followups(id TEXT PRIMARY KEY,person_id TEXT NOT NULL REFERENCES people(id),description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','done','cancelled')),due_on TEXT,evidence_message_id TEXT REFERENCES messages(id));
CREATE TABLE matches(id TEXT PRIMARY KEY,need_id TEXT NOT NULL REFERENCES needs(id),provider_id TEXT NOT NULL REFERENCES people(id),reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'suggested' CHECK(status IN ('suggested','reviewed','permission_requested','introduced','dismissed')),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(need_id,provider_id));
CREATE INDEX messages_sender ON messages(sender_id,sent_at);
CREATE INDEX needs_owner_status ON needs(person_id,status);
CREATE INDEX facts_person ON facts(person_id);
CREATE INDEX offers_skill ON offers(skill);
CREATE VIEW searchable AS
SELECT 'message' AS kind,id,sender_id AS person_id,body AS text FROM messages
UNION ALL SELECT 'fact',id,person_id,statement FROM facts
UNION ALL SELECT 'need',id,person_id,title||' '||description FROM needs
UNION ALL SELECT 'offer',id,person_id,skill||' '||COALESCE(description,'') FROM offers
UNION ALL SELECT 'followup',id,person_id,description FROM followups;
CREATE VIEW potential_matches AS SELECT n.id AS need_id,n.person_id AS seeker_id,o.person_id AS provider_id,ns.skill,o.willingness,o.source_id AS offer_source_id FROM needs n JOIN need_skills ns ON ns.need_id=n.id JOIN offers o ON lower(o.skill)=lower(ns.skill) WHERE n.status IN ('open','needs_confirmation') AND n.person_id<>o.person_id AND o.willingness<>'unavailable';
