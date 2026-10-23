"""Localize export labels without changing exporter names, parameter keys or values."""
from pyqtgraph.GraphicsScene.exportDialog import ExportDialog


class PortugueseExportDialog(ExportDialog):
    def __init__(self, scene):
        super().__init__(scene)
        self.resize(680, 640)
        self.ui.gridLayout.setSpacing(6)
        self.ui.gridLayout.setRowStretch(1, 2)
        self.ui.gridLayout.setRowStretch(3, 1)
        self.ui.gridLayout.setRowStretch(5, 3)

    def updateItemList(self, select=None):
        super().updateItemList(select)
        self.ui.itemTree.topLevelItem(0).setText(0, 'Toda a área do gráfico')

    def updateItemTree(self, item, treeItem, select=None):
        # The base method adds its row before visiting children.
        before = treeItem.childCount()
        super().updateItemTree(item, treeItem, select)
        if treeItem.childCount() > before:
            child = treeItem.child(before)
            child.setText(0, {'Plot': 'Gráfico', 'ViewBox': 'Área de visualização'}.get(child.text(0), child.text(0)))

    def exportFormatChanged(self, item, prev):
        super().exportFormatChanged(item, prev)
        if self.currentExporter is None:
            return
        params = self.currentExporter.parameters()
        if params is None:
            return
        params.setOpts(title='Opções')
        for param in params.children():
            if param.name() == 'separator':
                param.setLimits({'Vírgula': 'comma', 'Tabulação': 'tab'})
            elif param.name() == 'columnMode':
                param.setLimits({'(x,y) por curva': '(x,y) per plot',
                                 '(x,y,y,y) para todas as curvas': '(x,y,y,y) for all plots'})
            elif param.name() == 'scaling stroke':
                param.setOpts(tip='Ative para ajustar a espessura dos traços conforme a escala da imagem.')
        # Rebuild after changing limits: 0.13.7 otherwise retains the old display label.
        self.ui.paramTree.setParameters(params, showTop=False)
