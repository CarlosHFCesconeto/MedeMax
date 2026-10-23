import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.storage import Repository
from app.services.core import Core
from app.ui.main_window import MainWindow

def test_presentation_keyboard_navigation_and_live_data(tmp_path):
    app=QApplication.instance() or QApplication([])
    repo=Repository(tmp_path/'db'); c=Core(repo); c.demo_multi()
    w=MainWindow(c); w.show(); w.activateWindow(); app.processEvents()
    dash=w.device_dashboard; first=next(iter(c.devices)); dash.open_device(first)
    c.start()
    QTest.qWait(250); app.processEvents()
    dash.present_btn.click(); app.processEvents()
    assert w.isFullScreen() and w.presentation
    assert w.header.isHidden() and w.nav.isHidden() and w.footer.isHidden()
    assert dash.focus==first and len(dash.values)==8 and len(dash.curves)==8
    assert dash.toolbar.isHidden()
    dash.options_btn.click(); assert not dash.toolbar.isHidden()
    dash.options_btn.click(); assert dash.toolbar.isHidden()
    dash.open_device(None); assert len(dash.values)==24 and len(dash.curves)==24
    QTest.qWait(250); w.tick()
    assert all(label.text() and '—' not in label.text() for label in dash.values.values())
    w.setFocus(); QTest.keyClick(w,Qt.Key_Escape); app.processEvents()
    assert not w.presentation and not w.isFullScreen()
    assert not w.header.isHidden() and not w.nav.isHidden() and not w.footer.isHidden()
    assert c.running and not dash.toolbar.isHidden()
    w.nav.setCurrentRow(1); app.processEvents(); w.setFocus(); QTest.keyClick(w,Qt.Key_F11); app.processEvents()
    assert w.presentation and w.nav.currentRow()==0
    dash.present_btn.click(); app.processEvents(); assert w.nav.currentRow()==1
    c.stop(); w.close(); app.processEvents()
