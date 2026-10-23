import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
from PySide6.QtWidgets import QApplication
from app.storage import Repository
from app.services.core import Core
from app.ui.main_window import MainWindow
from app.ui.forms import Editor
from app.models import Tag,Device


def test_gui_start_forms_live_updates_and_close(tmp_path):
    app=QApplication.instance() or QApplication([])
    repo=Repository(tmp_path/'db'); core=Core(repo); core.demo()
    w=MainWindow(core); w.show()
    d=next(iter(core.devices.values()))
    form=Editor(Tag(device_id=d.id),core,w)
    form.inputs['scale'].setText('0,1'); form.save()
    assert form.result_obj.scale==.1
    form=Editor(Device(),core,w)
    form.inputs['transport'].setCurrentIndex(1)
    assert not form.form.isRowVisible(form.inputs['port'])
    assert form.form.isRowVisible(form.inputs['host'])
    assert w.window_combo.itemData(w.window_combo.count()-1)==86400
    assert w.auto_axes.isChecked()
    w.preset.setCurrentIndex(5)
    args=w.history_args()
    assert args[2]-args[1]>=28*86400
    w.show_history(repo.history_overview(*args))
    assert w.history_plot.getViewBox().state["autoRange"]==[True,True]
    w.start()
    deadline=time.monotonic()+.8
    while time.monotonic()<deadline: app.processEvents(); time.sleep(.01)
    assert w.watch.rowCount()==4
    assert w.watch.item(0,3).text()=='OK'
    assert len(w.curves)==4
    core.stop(); w.close(); app.processEvents()
