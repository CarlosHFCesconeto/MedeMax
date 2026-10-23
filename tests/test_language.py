import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import csv
from dataclasses import asdict
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLineEdit
from app.models import Device, Tag, AlarmRule, Sample
from app.storage import Repository
from app.services.core import Core
from app.ui.forms import Editor
from app.ui.main_window import MainWindow
from app.ui.language import show_export_dialog


def test_portuguese_dialogs_and_forms_keep_protocol_values(tmp_path):
    app = QApplication.instance() or QApplication([])
    repo = Repository(tmp_path/'db'); core = Core(repo)
    device = Device(name='Online', transport='TCP', host='192.168.10.111')
    core.save(device)
    tag = Tag(name='Save', device_id=device.id, function=4, data_type='FLOAT32',
              count=2, byte_order='little', word_order='big')
    core.save(tag)
    rule = AlarmRule(tag_id=tag.id, condition='offline')
    for obj in (device, tag, rule):
        editor = Editor(obj, core)
        assert editor.windowTitle() in ('Configurar dispositivo', 'Configurar medição (tag)', 'Configurar regra de alarme')
        buttons = editor.findChild(QDialogButtonBox)
        assert buttons.button(QDialogButtonBox.Save).text() == 'Salvar'
        assert buttons.button(QDialogButtonBox.Cancel).text() == 'Cancelar'
        editor.save()
        assert asdict(editor.result_obj) == asdict(obj)
        editor.close()
    buttons = QDialogButtonBox(QDialogButtonBox.Apply|QDialogButtonBox.Yes|QDialogButtonBox.No)
    assert {b.text().replace('&','') for b in buttons.buttons()} == {'Aplicar','Sim','Não'}
    text = QLineEdit(); menu = text.createStandardContextMenu()
    labels = [a.text().replace('&','').split('\t')[0] for a in menu.actions()]
    assert {'Desfazer','Refazer','Recortar','Copiar','Colar','Excluir','Selecionar tudo'} <= set(labels)
    assert QLocale().monthName(1) == 'janeiro'
    repo.close()


def test_translated_status_simulation_menus_and_export_preserve_data(tmp_path):
    app = QApplication.instance() or QApplication([])
    repo = Repository(tmp_path/'db'); core = Core(repo); core.demo()
    window = MainWindow(core); window.timer.stop(); window.show(); app.processEvents()
    try:
        assert window.nav.item(0).text() == 'Dashbord'
        assert 'Tags' in [window.nav.item(i).text() for i in range(window.nav.count())]
        assert window.devices_table.item(0,3).text() == 'Sim'
        modes = []
        core.set_simulation = modes.append
        window.sim_mode.setCurrentIndex(window.sim_mode.findData('offline'))
        window.sim_mode.setCurrentIndex(window.sim_mode.findData('timeout'))
        assert modes == ['offline','timeout']
        tag = next(iter(core.tags.values()))
        core.latest[tag.id] = Sample(1, tag.id, tag.device_id, None, 'Timeout')
        window.tick()
        assert window.watch.item(0,3).text() == 'Parado • Tempo de resposta excedido'
        assert core.latest[tag.id].quality == 'Timeout'
        for plot in (window.plot, window.history_plot, *window.device_dashboard.plots):
            assert [a.text() for a in plot.plotItem.vb.menu.actions()][1:3] == ['Eixo X','Eixo Y']
            assert plot.plotItem.ctrl.downsampleCheck.text() == 'Redução de pontos'
            assert 'Minimum' not in plot.plotItem.vb.menu.ctrl[0].minText.toolTip()
        plot = window.history_plot
        plot.plot([1,2,3],[4,5,6],name='Online')
        plot.scene().contextMenuItem = plot.plotItem
        show_export_dialog(plot.scene())
        dialog = plot.scene().exportDialog
        assert dialog.windowTitle() == 'Exportar'
        assert dialog.ui.itemTree.topLevelItem(0).text(0) == 'Toda a área do gráfico'
        for i in range(dialog.ui.formatList.count()):
            item = dialog.ui.formatList.item(i)
            if item.expClass.__name__ == 'CSVExporter':
                dialog.ui.formatList.setCurrentItem(item); break
        assert item.text() == 'CSV dos dados originais do gráfico'
        params = dialog.currentExporter.parameters()
        params.param('separator').setValue('tab')
        params.param('columnMode').setValue('(x,y,y,y) for all plots')
        path = tmp_path/'graph.tsv'
        dialog.currentExporter.export(str(path))
        with path.open() as stream:
            rows = list(csv.reader(stream,delimiter='\t'))
        assert 'Online' in str(rows[0])
        assert [[float(v) for v in row] for row in rows[1:]] == [[1,4],[2,5],[3,6]]
        dialog.close()
    finally:
        window.close(); app.processEvents(); repo.close()
