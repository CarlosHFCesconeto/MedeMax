"""SQLite repository: persistent connection, WAL, indexed history, batched writes."""
import csv
import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from .models import Device, Tag, AlarmRule


class Repository:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.RLock()
        self.con = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS config(kind TEXT, id TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY, ts REAL NOT NULL, tag TEXT NOT NULL, device TEXT NOT NULL, value REAL, quality TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS samples_tag_ts ON samples(tag,ts);
        CREATE INDEX IF NOT EXISTS samples_ts ON samples(ts);
        CREATE TABLE IF NOT EXISTS alarms(id INTEGER PRIMARY KEY, rule TEXT, tag TEXT, name TEXT, severity TEXT, message TEXT, activated REAL, value REAL, acknowledged REAL, normalized REAL);
        CREATE INDEX IF NOT EXISTS alarms_active ON alarms(normalized);
        CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, ts REAL, tag TEXT, value REAL, status TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS retired_alarm_rules(rule TEXT PRIMARY KEY, retired REAL NOT NULL);
        PRAGMA user_version=1;
        ''')
        self.con.commit()

    def save(self, obj):
        obj.validate()
        with self.lock, self.con:
            self.con.execute('INSERT OR REPLACE INTO config VALUES(?,?,?)',(type(obj).__name__,obj.id,json.dumps(asdict(obj))))

    def load(self, cls):
        with self.lock:
            return [cls(**json.loads(r[0])) for r in self.con.execute('SELECT body FROM config WHERE kind=? ORDER BY rowid',(cls.__name__,))]

    def save_many(self, objects):
        objects = list(objects)
        for obj in objects: obj.validate()
        with self.lock, self.con:
            self.con.executemany('INSERT OR REPLACE INTO config VALUES(?,?,?)',
                [(type(obj).__name__, obj.id, json.dumps(asdict(obj))) for obj in objects])

    def remove(self, cls, identifier):
        with self.lock, self.con: self.con.execute('DELETE FROM config WHERE kind=? AND id=?',(cls.__name__,identifier))

    def device_removal_plan(self, identifier):
        with self.lock:
            device=next((d for d in self.load(Device) if d.id==identifier),None)
            if device is None: raise ValueError('Dispositivo não encontrado')
            tags={t.id for t in self.load(Tag) if t.device_id==identifier}
            rules={r.id for r in self.load(AlarmRule) if r.tag_id in tags}
            active=sum(self.con.execute('SELECT COUNT(*) FROM alarms WHERE rule=? AND normalized IS NULL '
                'AND NOT EXISTS (SELECT 1 FROM retired_alarm_rules WHERE rule=alarms.rule)',(rule,)).fetchone()[0] for rule in rules)
            return dict(device_id=identifier,name=device.name,tag_ids=sorted(tags),rule_ids=sorted(rules),active_alarms=active)

    def remove_device(self, identifier, retired_at, expected=None):
        """Delete one configuration subtree atomically; preserve measurements and event records."""
        with self.lock, self.con:
            self.con.execute('BEGIN IMMEDIATE')
            plan=self.device_removal_plan(identifier)
            if expected is not None and plan != expected:
                raise ValueError('Os vínculos do dispositivo mudaram. Revise a confirmação antes de excluir.')
            self.con.executemany('INSERT OR IGNORE INTO retired_alarm_rules VALUES(?,?)',
                                 [(rule,retired_at) for rule in plan['rule_ids']])
            entries=[('AlarmRule',rule) for rule in plan['rule_ids']]
            entries += [('Tag',tag) for tag in plan['tag_ids']]
            entries.append(('Device',identifier))
            self.con.executemany('DELETE FROM config WHERE kind=? AND id=?',entries)
            for key,removed in [('dashboard_devices',{identifier}),('dashboard_tags',set(plan['tag_ids'])),
                                ('dashboard_measurements',set(plan['tag_ids']))]:
                selected=self.setting(key,None)
                if isinstance(selected,list):
                    self.con.execute('UPDATE config SET body=? WHERE kind=? AND id=?',
                                     (json.dumps([item for item in selected if item not in removed]),'setting',key))
            return plan

    def setting(self, key, default=None):
        with self.lock:
            row = self.con.execute('SELECT body FROM config WHERE kind=? AND id=?',('setting',key)).fetchone()
            return json.loads(row[0]) if row else default

    def set_setting(self, key, value):
        with self.lock, self.con: self.con.execute('INSERT OR REPLACE INTO config VALUES(?,?,?)',('setting',key,json.dumps(value)))

    def append(self, samples):
        with self.lock, self.con:
            self.con.executemany('INSERT INTO samples(ts,tag,device,value,quality) VALUES(?,?,?,?,?)',[(s.timestamp,s.tag_id,s.device_id,s.value,s.quality) for s in samples])

    def history(self, tags, start, end, limit=20000):
        if not tags: return []
        with self.lock:
            return [dict(r) for r in self.con.execute(f'SELECT * FROM samples WHERE tag IN ({",".join("?" for _ in tags)}) AND ts BETWEEN ? AND ? ORDER BY ts DESC,id DESC LIMIT ?',(*tags,start,end,limit))][::-1]

    def history_overview(self, tags, start, end, buckets=1200):
        """Full-period overview on a separate reader; bounded output, peaks retained."""
        if not tags: return {'rows': [], 'total': 0, 'recent': []}
        width=max((end-start)/buckets, .001)
        rows=[]; total=0
        with sqlite3.connect(self.path, timeout=5) as con:
            con.row_factory=sqlite3.Row
            for tag in tags:
                result=con.execute("""SELECT CAST((ts-?)/? AS INTEGER) AS bucket,
                    MIN(ts) AS first_ts, MAX(ts) AS last_ts, COUNT(*) AS n,
                    MIN(CASE WHEN quality='OK' THEN value END) AS low,
                    MAX(CASE WHEN quality='OK' THEN value END) AS high,
                    SUM(CASE WHEN quality!='OK' THEN 1 ELSE 0 END) AS bad
                    FROM samples WHERE tag=? AND ts BETWEEN ? AND ?
                    GROUP BY bucket ORDER BY bucket""", (start,width,tag,start,end))
                for r in result:
                    total+=r['n']
                    for value in (r['low'],r['high']):
                        if value is not None:
                            rows.append(dict(tag=tag,ts=r['first_ts'],value=value,quality='OK'))
                    if r['bad']:
                        rows.append(dict(tag=tag,ts=r['last_ts'],value=None,quality='Falha no intervalo'))
            recent=[dict(r) for r in con.execute(f'SELECT * FROM samples WHERE tag IN ({",".join("?" for _ in tags)}) AND ts BETWEEN ? AND ? ORDER BY ts DESC,id DESC LIMIT 500',(*tags,start,end))][::-1]
        return {'rows':rows,'total':total,'recent':recent}

    def export(self, destination, tags, start, end):
        if not tags: raise ValueError('Selecione tags')
        # Independent read connection and streaming cursor: no full export in RAM.
        names = {t.id:t.name for t in self.load(Tag)}
        with sqlite3.connect(self.path,timeout=5) as con, open(destination,'w',newline='',encoding='utf-8-sig') as f:
            writer = csv.writer(f,delimiter=';')
            writer.writerow(['data_hora_utc','tag','tag_id','dispositivo_id','valor','qualidade'])
            rows = con.execute(f'SELECT ts,tag,device,value,quality FROM samples WHERE tag IN ({",".join("?" for _ in tags)}) AND ts BETWEEN ? AND ? ORDER BY ts,id',(*tags,start,end))
            n = 0
            for ts,tag,device,value,quality in rows:
                writer.writerow([datetime.fromtimestamp(ts,timezone.utc).isoformat(),names.get(tag,tag),tag,device,str(value).replace('.',',') if value is not None else '',quality]); n += 1
            return n

    def prune(self, before):
        # Limited chunks bound write-lock duration; freed pages are reused by SQLite.
        with self.lock, self.con:
            return self.con.execute('DELETE FROM samples WHERE id IN (SELECT id FROM samples WHERE ts<? LIMIT 10000)',(before,)).rowcount

    def alarm_open(self, rule, sample):
        with self.lock, self.con:
            return self.con.execute('INSERT INTO alarms(rule,tag,name,severity,message,activated,value) VALUES(?,?,?,?,?,?,?)',(rule.id,rule.tag_id,rule.name,rule.severity,rule.message,sample.timestamp,sample.value)).lastrowid

    def alarm_normalize(self, event_id, ts):
        with self.lock, self.con: self.con.execute('UPDATE alarms SET normalized=? WHERE id=? AND normalized IS NULL',(ts,event_id))

    def acknowledge(self, event_id, ts):
        with self.lock, self.con: self.con.execute('UPDATE alarms SET acknowledged=? WHERE id=? AND acknowledged IS NULL',(ts,event_id))

    def alarms(self, active=False):
        with self.lock:
            return [dict(r) for r in self.con.execute('SELECT a.*,r.retired FROM alarms a '
                'LEFT JOIN retired_alarm_rules r ON r.rule=a.rule '+
                ('WHERE a.normalized IS NULL AND r.rule IS NULL ' if active else '')+
                'ORDER BY a.id DESC LIMIT 2000')]

    def command(self, identifier, ts, tag, value, status, detail=''):
        with self.lock, self.con: self.con.execute('INSERT OR REPLACE INTO commands VALUES(?,?,?,?,?,?)',(identifier,ts,tag,value,status,detail))

    def close(self):
        with self.lock: self.con.close()
