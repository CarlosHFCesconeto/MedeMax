import time
import threading
import pytest
from app.storage import Repository
from app.services.core import Core,scan
from app.models import Device,Tag


def wait_for(fn,timeout=5):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if fn(): return
        time.sleep(.025)
    assert fn()


def test_headless_acquisition_write_alarm_and_restart(tmp_path):
    repo=Repository(tmp_path/'db'); core=Core(repo); core.demo(); core.start()
    try:
        wait_for(lambda:len(core.latest)==4)
        tag=next(iter(core.tags.values()))
        assert core.write(tag.id,222.2).result(3)[0]=='Confirmado'
        wait_for(lambda:core.latest[tag.id].value==pytest.approx(222.2))
        core.set_simulation('alarme'); wait_for(lambda:len(repo.alarms(active=True))==1)
        core.set_simulation('offline'); wait_for(lambda:all(s.quality=='Offline' for s in core.latest.values()))
        with pytest.raises(RuntimeError): core.write(tag.id,1)
        core.set_simulation('normal'); wait_for(lambda:all(s.quality=='OK' for s in core.latest.values()),8)
    finally: assert core.stop()
    assert repo.history([tag.id],0,time.time())
    core.reload(); assert len(core.tags)==4
    repo.close()


def test_shared_serial_bus_validation(tmp_path):
    repo=Repository(tmp_path/'db'); core=Core(repo)
    core.save(Device(name='a',port='COM5',baudrate=9600)); core.save(Device(name='b',port='com5',baudrate=19200,unit_id=2))
    with pytest.raises(ValueError): core.start()
    assert not core.running; repo.close()


def test_scanner_bounded_and_cancel():
    d=Device(transport='SIM'); rows=[]; cancel=threading.Event()
    with pytest.raises(ValueError): scan(d,3,0,512,cancel,lambda *x:rows.append(x))
    scan(d,3,0,2,cancel,lambda *x:rows.append(x))
    assert len(rows)==3 and all(x[2]=='OK' for x in rows)
    cancel.set(); scan(d,3,0,2,cancel,lambda *x:rows.append(x)); assert len(rows)==3
