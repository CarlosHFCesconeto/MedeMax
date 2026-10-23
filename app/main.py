import argparse
import atexit
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import time
from .storage import Repository
from .session import SessionLock
from .services.core import Core


def main():
    parser=argparse.ArgumentParser(description='MedeMax • SCADA desktop')
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--seconds',type=float,default=0,help='Duração headless; 0 = contínuo')
    parser.add_argument('--smoke-test',action='store_true',help='Abrir interface e fechar automaticamente')
    args=parser.parse_args()
    root=args.data_dir or Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'MonitorModbus'
    if args.demo: root = root / 'simulation'
    root.mkdir(parents=True,exist_ok=True); (root/'logs').mkdir(exist_ok=True)
    handler=RotatingFileHandler(root/'logs'/'monitor.log',maxBytes=2_000_000,backupCount=5,encoding='utf-8')
    logging.basicConfig(level=logging.INFO,handlers=[handler],format='%(asctime)s %(levelname)s %(name)s %(message)s')
    logging.info('Início MedeMax 0.3.6')
    try: session=SessionLock(root/'session.lock')
    except RuntimeError as e:
        if args.headless: raise SystemExit(str(e))
        from PySide6.QtWidgets import QApplication,QMessageBox
        application=QApplication(sys.argv)
        from .ui.language import install_translations
        install_translations(); QMessageBox.warning(None,'MedeMax',str(e)); return
    atexit.register(session.close)
    repo=Repository(root/'monitor.db'); core=Core(repo)
    if args.demo: core.demo()
    if args.headless:
        core.start(); deadline=time.monotonic()+args.seconds if args.seconds>0 else float('inf')
        try:
            while time.monotonic()<deadline: time.sleep(.1)
        except KeyboardInterrupt: pass
        finally:
            if core.stop(): repo.close()
        return
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    import pyqtgraph as pg
    from .ui.main_window import MainWindow
    app=QApplication(sys.argv); app.setApplicationName('MedeMax'); app.setStyle('Fusion')
    pg.setConfigOptions(antialias=False)
    window=MainWindow(core); window.show()
    if args.demo: window.start()
    if args.smoke_test: QTimer.singleShot(1500,window.close)
    sys.exit(app.exec())
