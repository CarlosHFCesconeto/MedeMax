import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from app.storage import Repository
from app.services.core import Core
from app.ui.main_window import MainWindow
from app.communication.transports import Simulator
from app.codec import decode

def test_multi_demo_and_navigation(tmp_path):
    app=QApplication.instance() or QApplication([])
    repo=Repository(tmp_path/'db'); core=Core(repo); core.demo_multi(); core.demo_multi()
    assert len(core.devices)==3 and len(core.tags)==24 and len(core.rules)==3
    for device in core.devices.values():
        sim=Simulator(device)
        tags=[t for t in core.tags.values() if t.device_id==device.id]
        assert len(tags)==8
        assert all(decode(sim.read(device.unit_id,t.function,t.address,t.count),t)>=0 for t in tags)
        sim.mode='alarme'
        assert decode(sim.read(device.unit_id,3,100,1),tags[0])>240
    w=MainWindow(core); w.show(); app.processEvents()
    dash=w.device_dashboard
    assert len(dash.plots)==3 and len(dash.curves)==24
    dash.mode.setCurrentIndex(1)
    assert len(dash.plots)==1 and len(dash.curves)==24
    dash.open_device(next(iter(core.devices)))
    assert len(dash.plots)==1 and len(dash.curves)==8 and len(dash.values)==8
    dash.quantity.setCurrentIndex(1)
    assert len(dash.curves)==4
    dash.open_device(None)
    assert len(dash.curves)==12
    core.start()
    import time
    time.sleep(.3); w.tick()
    assert len(core.latest)==24
    core.stop(); w.close(); app.processEvents()

def test_selection_modes_styles_and_persistence(tmp_path):
    from app.ui.dashboard import Dashboard
    from PySide6.QtWidgets import QComboBox
    app=QApplication.instance() or QApplication([])
    repo=Repository(tmp_path/'db'); core=Core(repo); core.demo_multi()
    dash=Dashboard(core); dash.rebuild()
    ids=list(core.devices); dash.set_devices(ids[:2]); assert len(dash.curves)==16
    dash.mode.setCurrentIndex(2); assert len(dash.plots)==2
    dash.mode.setCurrentIndex(3); assert len(dash.plots)==16
    dash.mode.setCurrentIndex(1); assert len(dash.plots)==1
    style=next(w for w in dash.body.findChildren(QComboBox) if w.count()==4)
    core.start()
    import time
    time.sleep(.2)
    for i in range(4):
        style.setCurrentIndex(i); dash.refresh()
        assert all(len(curve.getData()[1])>0 for curve in dash.curves.values())
    assert all(core.devices[core.tags[t].device_id].name in c.name() for t,c in dash.curves.items())
    dash.set_devices([]); assert not dash.curves
    again=Dashboard(core); again.rebuild(); assert not again.curves
    assert len(core.latest)==24  # Hidden devices still acquire.
    dash.set_devices(ids[:1]); again.rebuild(); assert len(again.curves)==8
    core.stop(); dash.close(); again.close(); repo.close()
