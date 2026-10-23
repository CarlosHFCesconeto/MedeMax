import csv
from app.models import Device,Tag,AlarmRule,Sample
from app.storage import Repository
from app.services.alarms import AlarmEngine
import pytest


def test_persistence_history_export_retention(tmp_path):
    path=tmp_path/'db.sqlite'; repo=Repository(path)
    d=Device(transport='SIM'); t=Tag(device_id=d.id); repo.save(d); repo.save(t)
    repo.append([Sample(1,t.id,d.id,1.5,'OK'),Sample(2,t.id,d.id,None,'Timeout'),Sample(3,'other',d.id,9,'OK')]); repo.close()
    repo=Repository(path)
    assert repo.load(Device)[0]==d and repo.load(Tag)[0]==t
    assert len(repo.history([t.id],0,2))==2
    dest=tmp_path/'out.csv'; assert repo.export(dest,[t.id],0,2)==2
    with dest.open(encoding='utf-8-sig') as f: rows=list(csv.reader(f,delimiter=';'))
    assert rows[1][4]=='1,5' and rows[2][4]==''
    assert repo.prune(2)==1
    assert len(repo.history([t.id],0,10))==1
    repo.close()


@pytest.mark.parametrize('condition,value,threshold,quality,expected',[('>',11,10,'OK',True),('<',9,10,'OK',True),('==',10,10,'OK',True),('ativo',1,0,'OK',True),('inativo',0,0,'OK',True),('offline',None,0,'Offline',True),('offline',None,0,'Timeout',True),('>',None,10,'Timeout',None),('>',9,10,'OK',False)])
def test_conditions(condition,value,threshold,quality,expected):
    assert AlarmEngine.matches(AlarmRule(tag_id='t',condition=condition,threshold=threshold),Sample(1,'t','d',value,quality)) is expected


def test_alarm_lifecycle_restart(tmp_path):
    repo=Repository(tmp_path/'db'); r=AlarmRule(tag_id='t',threshold=10)
    engine=AlarmEngine(repo,[r]); high=Sample(1,'t','d',11,'OK')
    engine.process(high); engine.process(high)
    assert len(repo.alarms())==1
    identifier=repo.alarms()[0]['id']; repo.acknowledge(identifier,2); repo.acknowledge(identifier,3)
    engine=AlarmEngine(repo,[r]); engine.process(high)
    assert len(repo.alarms())==1
    engine.process(Sample(4,'t','d',None,'Timeout')); assert len(repo.alarms(active=True))==1
    engine.process(Sample(5,'t','d',9,'OK')); assert repo.alarms(active=True)==[]
    event=repo.alarms()[0]; assert event['acknowledged']==2 and event['normalized']==5
    engine.process(Sample(6,'t','d',12,'OK')); assert len(repo.alarms())==2
    repo.close()
