import time
import pytest
from app.models import Device, Tag
from app.profiles import measurement_tags, read_plan, MEASUREMENT_MAP
from app.storage import Repository
from app.services.core import Core


def wait_for(predicate):
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        if predicate(): return
        time.sleep(.01)
    assert predicate()


def test_map_applies_to_one_device_without_duplicates_or_overwriting(tmp_path):
    repo=Repository(tmp_path/'db'); core=Core(repo)
    first=Device(name='Medidor 1', port='COM7', unit_id=3, interval_ms=700)
    second=Device(name='Medidor 2', port='COM7', unit_id=4)
    core.save(first); core.save(second)
    assert core.apply_measurement_map(first.id)==26
    original_ids=set(core.tags)
    assert core.apply_measurement_map(first.id)==0
    assert set(core.tags)==original_ids
    assert all(t.device_id==first.id and t.function==4 and not t.writable for t in core.tags.values())
    assert core.devices[first.id].port=='COM7' and core.devices[first.id].unit_id==3
    assert core.devices[first.id].interval_ms==700 and core.devices[first.id].read_blocks
    assert not core.devices[second.id].read_blocks
    assert [t.address for t in core.tags.values()]==list(range(26))
    assert [t.scale for t in core.tags.values()]==[.01]*17+[1]*9
    assert 'Tensão N' not in [t.name for t in core.tags.values()]
    assert 'Corrente 4' in [t.name for t in core.tags.values()]
    from app.ui.dashboard import measurement_card
    current4=next(t for t in core.tags.values() if t.address==6)
    assert measurement_card(current4)==(1,3,'Corrente 4')
    repo.close()


def test_conflicting_map_does_not_partially_save(tmp_path):
    repo=Repository(tmp_path/'db'); core=Core(repo); device=Device(); core.save(device)
    tag=Tag(name='Outra medição',device_id=device.id,function=4,address=25,scale=.5)
    core.save(tag)
    with pytest.raises(ValueError, match='incompatível'): core.apply_measurement_map(device.id)
    core.reload()
    assert list(core.tags)==[tag.id] and not core.devices[device.id].read_blocks
    repo.close()


@pytest.mark.parametrize('grouped,requests',[(True,1),(False,26)])
def test_worker_decodes_complete_map_and_stores_samples(tmp_path,monkeypatch,grouped,requests):
    calls=[]
    raw=[22035,22100,21990,525,610,700,40]+[6000]*7+[95,96,97]+[1000,1100,1200,65536-250,200,100]+[1100,1200,1300]
    class Transport:
        def read(self,unit,function,address,count):
            calls.append((unit,function,address,count))
            return raw[address:address+count]
        def close(self): pass
    monkeypatch.setattr('app.services.core.make_transport',lambda *args:Transport())
    repo=Repository(tmp_path/'db'); core=Core(repo)
    device=Device(transport='TCP',unit_id=7,interval_ms=60000); core.save(device)
    core.apply_measurement_map(device.id,power_type='INT16',group_reads=grouped)
    core.start()
    try:
        wait_for(lambda:len(core.latest)==26)
        assert len(calls)==requests
        if grouped: assert calls==[(7,4,0,26)]
        by_address={t.address:core.latest[t.id] for t in core.tags.values()}
        assert by_address[0].value==pytest.approx(220.35)
        assert by_address[3].value==pytest.approx(5.25)
        assert by_address[7].value==60
        assert by_address[14].value==pytest.approx(.95)
        assert by_address[20].value==-250
        assert all(s.quality=='OK' for s in by_address.values())
        if grouped: assert len({s.timestamp for s in by_address.values()})==1
    finally: assert core.stop()
    assert len(repo.history(list(core.tags),0,time.time()))==26
    repo.close()


@pytest.mark.parametrize('error,quality',[(TimeoutError('sem resposta'),'Timeout'),(ConnectionError('desconectado'),'Offline'),(ValueError('exceção Modbus'),'Erro Modbus')])
def test_failed_block_marks_every_measurement_without_fabricated_values(tmp_path,monkeypatch,error,quality):
    class Transport:
        def read(self,*args): raise error
        def close(self): pass
    monkeypatch.setattr('app.services.core.make_transport',lambda *args:Transport())
    repo=Repository(tmp_path/'db'); core=Core(repo); device=Device(); core.save(device)
    core.apply_measurement_map(device.id); core.start()
    try:
        wait_for(lambda:len(core.latest)==26)
        assert all(s.quality==quality and s.value is None for s in core.latest.values())
    finally: assert core.stop()
    repo.close()


def test_grouping_respects_disabled_tags_gaps_functions_and_protocol_limit():
    tags=[Tag(address=n) for n in range(126)]
    plan=read_plan(tags,True)
    assert [(a,n) for _,a,n,_ in plan]==[(0,125),(125,1)]
    plan=read_plan([Tag(address=0),Tag(address=2),Tag(address=3,function=4)],True)
    assert [(f,a,n) for f,a,n,_ in plan]==[(3,0,1),(3,2,1),(4,3,1)]
    # Multiword values retain all words and share overlapping reads.
    plan=read_plan([Tag(address=0,data_type='FLOAT32',count=2),Tag(address=1)],True)
    assert len(plan)==1 and plan[0][2]==2


def test_three_meters_share_serial_worker_and_keep_measurements_separate(tmp_path,monkeypatch):
    calls=[]
    class Transport:
        def read(self,unit,function,address,count):
            calls.append((unit,function,address,count))
            return [unit*100]*count
        def close(self): pass
    monkeypatch.setattr('app.services.core.make_transport',lambda *args:Transport())
    repo=Repository(tmp_path/'db'); core=Core(repo)
    for unit in (1,2,3):
        d=Device(name=f'Medidor {unit}',port='COM7',unit_id=unit,interval_ms=60000)
        core.save(d); core.apply_measurement_map(d.id)
    # A disabled measurement must not be polled or published.
    last=next(t for t in core.tags.values() if t.device_id==d.id and t.address==25)
    from dataclasses import replace
    core.save(replace(last,polling=False))
    core.start()
    try:
        wait_for(lambda:len(core.latest)==77)
        assert len(core.workers)==1
        assert calls==[(1,4,0,26),(2,4,0,26),(3,4,0,25)]
        assert last.id not in core.latest
        for device in core.devices.values():
            voltage=next(t for t in core.tags.values() if t.device_id==device.id and t.address==0)
            assert core.latest[voltage.id].value==device.unit_id
    finally: assert core.stop()
    repo.close()


def test_profile_simulation_all_measurements_and_existing_demo_survive(tmp_path):
    repo=Repository(tmp_path/'db'); core=Core(repo); core.demo()
    old_ids=set(core.tags)
    core.demo_measurement_map(); core.demo_measurement_map()
    assert len(core.tags)==30 and old_ids <= set(core.tags)
    device=next(d for d in core.devices.values() if d.measurement_profile==MEASUREMENT_MAP)
    core.start()
    try:
        wait_for(lambda:len(core.latest)==30)
        with pytest.raises(RuntimeError): core.apply_measurement_map(device.id)
        assert all(s.quality=='OK' for s in core.latest.values())
    finally: assert core.stop()
    repo.close()


def test_map_dialog_preview_and_device_editor_backward_compatibility(tmp_path):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from app.ui.forms import Editor,MeasurementMapDialog
    from app.ui.main_window import MainWindow
    app=QApplication.instance() or QApplication([])
    repo=Repository(tmp_path/'db'); core=Core(repo); core.demo_measurement_map()
    device=next(iter(core.devices.values()))
    dialog=MeasurementMapDialog(device)
    assert dialog.preview.rowCount()==26 and dialog.group_reads.isChecked()
    dialog.power_type.setCurrentText('INT16')
    assert dialog.preview.item(20,3).text()=='INT16'
    assert dialog.preview.item(23,3).text()=='UINT16'
    editor=Editor(device,core)
    assert 'measurement_profile' not in editor.inputs and editor.inputs['read_blocks'].isChecked()
    window=MainWindow(core); window.show(); app.processEvents()
    assert window.watch.rowCount()==26 and len(window.device_dashboard.curves)==26
    window.device_dashboard.open_device(device.id)
    assert len(window.device_dashboard.values)==26
    window.close(); dialog.close(); editor.close(); app.processEvents()
