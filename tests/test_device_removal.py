import sqlite3
import time
import pytest
from app.models import Device,Tag,AlarmRule,Sample
from app.services.core import Core
from app.storage import Repository


def installation(tmp_path):
    repo=Repository(tmp_path/'db'); core=Core(repo)
    first=Device(name='Medidor a remover',transport='SIM')
    second=Device(name='Medidor preservado',transport='SIM')
    core.save(first); core.save(second)
    core.apply_measurement_map(first.id); core.apply_measurement_map(second.id)
    for device in (first,second):
        tag=next(t for t in core.tags.values() if t.device_id==device.id and t.address==0)
        core.save(AlarmRule(name='Tensão alta '+device.name,tag_id=tag.id,threshold=230))
        repo.append([Sample(10,tag.id,device.id,240,'OK')])
    for rule in core.rules: core.alarms.process(Sample(11,rule.tag_id,core.tags[rule.tag_id].device_id,240,'OK'))
    return repo,core,first,second


def test_delete_device_removes_dependencies_but_preserves_other_device_and_history(tmp_path):
    repo,core,first,second=installation(tmp_path)
    ids={t.id for t in core.tags.values() if t.device_id==first.id}
    survivor_ids=set(core.tags)-ids
    repo.set_setting('dashboard_devices',[first.id,second.id])
    repo.set_setting('dashboard_tags',list(core.tags))
    repo.set_setting('dashboard_measurements',list(core.tags))
    plan=core.device_removal_plan(first.id)
    assert len(plan['tag_ids'])==26 and len(plan['rule_ids'])==1 and plan['active_alarms']==1
    core.remove(Device,first.id,expected_dependencies=plan)
    assert set(core.devices)=={second.id} and set(core.tags)==survivor_ids
    assert len(core.rules)==1 and core.rules[0].tag_id in survivor_ids
    assert repo.setting('dashboard_devices')==[second.id]
    assert set(repo.setting('dashboard_tags'))==survivor_ids
    assert set(repo.setting('dashboard_measurements'))==survivor_ids
    assert len(repo.history(list(ids),0,20))==1
    assert len(repo.alarms())==2 and len(repo.alarms(active=True))==1
    retired=next(e for e in repo.alarms() if e['tag'] in ids)
    assert retired['retired'] is not None and retired['normalized'] is None
    core.reload(); assert len(core.alarms.active)==1
    repo.close(); reopened=Repository(tmp_path/'db')
    assert len(reopened.load(Tag))==26 and len(reopened.alarms(active=True))==1
    assert len(reopened.history(list(ids),0,20))==1
    reopened.close()


def test_deletion_is_atomic_even_when_storage_fails_midway(tmp_path):
    repo,core,first,second=installation(tmp_path)
    before=core.device_removal_plan(first.id)
    repo.con.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON config WHEN OLD.kind='Tag' BEGIN SELECT RAISE(ABORT,'falha de teste'); END")
    with pytest.raises(sqlite3.IntegrityError): core.remove(Device,first.id)
    assert repo.device_removal_plan(first.id)==before
    assert len(repo.load(Tag))==52 and len(repo.load(AlarmRule))==2
    assert repo.con.execute('SELECT COUNT(*) FROM retired_alarm_rules').fetchone()[0]==0
    assert len(repo.alarms(active=True))==2
    repo.close()


def test_changed_dependencies_require_a_new_confirmation(tmp_path):
    repo,core,first,second=installation(tmp_path)
    plan=core.device_removal_plan(first.id)
    repo.save(Tag(name='Nova medição',device_id=first.id,address=100))
    with pytest.raises(ValueError,match='mudaram'): core.remove(Device,first.id,expected_dependencies=plan)
    assert len(repo.load(Device))==2 and len(repo.load(Tag))==53
    repo.close()


def test_empty_device_and_deletion_while_acquiring(tmp_path):
    repo=Repository(tmp_path/'db'); core=Core(repo)
    d=Device(transport='SIM'); core.save(d)
    assert core.device_removal_plan(d.id)['tag_ids']==[]
    core.start()
    try:
        with pytest.raises(RuntimeError): core.device_removal_plan(d.id)
        with pytest.raises(RuntimeError): core.remove(Device,d.id)
    finally: assert core.stop()
    core.remove(Device,d.id)
    assert not core.devices
    with pytest.raises(ValueError): core.remove(Device,d.id)
    repo.close()


@pytest.mark.parametrize('confirm',[False,True])
def test_ui_confirmation_shows_counts_cancel_and_delete(tmp_path,confirm):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication,QMessageBox
    from app.ui.main_window import MainWindow
    app=QApplication.instance() or QApplication([])
    repo,core,first,second=installation(tmp_path)
    window=MainWindow(core); window.show(); app.processEvents()
    window.device_dashboard.open_device(first.id)
    captured=[]
    def answer():
        box=app.activeModalWidget()
        assert isinstance(box,QMessageBox)
        captured.append(box.text())
        assert 'Tags vinculadas: 26' in box.text() and 'Regras de alarme vinculadas: 1' in box.text()
        assert 'Alarmes ativos: 1' in box.text()
        assert box.defaultButton().text()=='Cancelar'
        button=next(b for b in box.buttons() if b.text()==('Excluir dispositivo' if confirm else 'Cancelar'))
        button.click()
    QTimer.singleShot(0,answer)
    window.delete(Device,first)
    assert captured and (first.id not in core.devices)==confirm
    if confirm:
        assert window.devices_table.rowCount()==1 and window.tags_table.rowCount()==26
        assert window.device_dashboard.focus is None
        window.show_alarms(repo.alarms())
        endings=[window.alarm_table.item(i,7).text() for i in range(window.alarm_table.rowCount())]
        assert any('Encerrado por exclusão' in text for text in endings)
    window.close(); app.processEvents()
