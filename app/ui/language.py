"""Portuguese UI labels; protocol values and user-provided names stay unchanged."""
from PySide6.QtCore import QLocale, QTranslator, QLibraryInfo, Qt
from PySide6.QtWidgets import QApplication
from .branding import asset_path


GRAPH_TEXT = {
    'ViewBox options': 'Opções de visualização', 'View All': 'Enquadrar todos os dados',
    'Mouse Mode': 'Modo do mouse', '3 button': '3 botões', '1 button': '1 botão',
    'Auto': 'Automático', 'Auto Pan Only': 'Apenas deslocamento automático',
    'Visible Data Only': 'Somente dados visíveis', 'Invert Axis': 'Inverter eixo',
    'Link Axis:': 'Vincular eixo:', 'Mouse Enabled': 'Interação com o mouse', 'None': 'Nenhum',
    'Plot Options': 'Opções do gráfico', 'Transforms': 'Transformações',
    'Power Spectrum (FFT)': 'Espectro de potência (FFT)',
    'Log X': 'Escala logarítmica X', 'Log Y': 'Escala logarítmica Y',
    'Downsample': 'Redução de pontos', 'Subsample': 'Subamostragem', 'Mean': 'Média',
    'Peak': 'Picos', 'Clip to View': 'Limitar à área visível', 'Average': 'Média de curvas',
    'Forget hidden traces': 'Desconsiderar curvas ocultas', 'Max Traces:': 'Máximo de curvas:',
    'Alpha': 'Transparência', 'Opacity': 'Opacidade', 'Grid': 'Grade',
    'Show X Grid': 'Mostrar grade X', 'Show Y Grid': 'Mostrar grade Y', 'Points': 'Pontos',
    'Export': 'Exportar', 'Export...': 'Exportar...', 'Copy': 'Copiar', 'Close': 'Fechar',
    'Export format': 'Formato de exportação', 'Export options': 'Opções de exportação',
    'Item to export:': 'Item a exportar:',
    'Image File (PNG, TIF, JPG, ...)': 'Arquivo de imagem (PNG, TIF, JPG, ...)',
    'Scalable Vector Graphics (SVG)': 'Imagem vetorial (SVG)',
    'CSV of original plot data': 'CSV dos dados originais do gráfico',
    'HDF5 Export: plot (x,y)': 'HDF5 dos dados do gráfico',
    'Matplotlib Window': 'Janela do Matplotlib', 'Printer': 'Impressora',
    'Print Document': 'Imprimir documento', 'width': 'Largura', 'height': 'Altura',
    'background': 'Fundo', 'antialias': 'Suavização de bordas',
    'invertValue': 'Inverter luminosidade',
    'scaling stroke': 'Ajustar espessura dos traços à escala',
    'separator': 'Separador', 'precision': 'Precisão', 'columnMode': 'Organização das colunas',
    'Name': 'Nome',
}

GRAPH_HELP = {
    'Links this axis with another view. When linked, both views will display the same data range.':
        'Vincula este eixo a outra visualização. Ambas passam a mostrar o mesmo intervalo de dados.',
    'Percent of data to be visible when auto-scaling. It may be useful to decrease this value for data with spiky noise.':
        'Percentual dos dados considerado no ajuste automático. Reduzir pode ajudar quando há picos de ruído.',
    'Automatically resize this axis whenever the displayed data is changed.':
        'Ajusta este eixo automaticamente quando os dados exibidos mudam.',
    'Set the range for this axis manually. This disables automatic scaling. ':
        'Define o intervalo deste eixo manualmente e desativa o ajuste automático.',
    'Minimum value to display for this axis.': 'Valor mínimo exibido neste eixo.',
    'Maximum value to display for this axis.': 'Valor máximo exibido neste eixo.',
    'Inverts the display of this axis. (+y points downward instead of upward)':
        'Inverte a direção deste eixo. No eixo Y, os valores positivos passam a apontar para baixo.',
    'Enables mouse interaction (panning, scaling) for this axis.':
        'Permite deslocar e ampliar este eixo com o mouse.',
    'When checked, the axis will only auto-scale to data that is visible along the orthogonal axis.':
        'Ajusta automaticamente considerando apenas os dados visíveis no outro eixo.',
    'When checked, the axis will automatically pan to center on the current data, but the scale along this axis will not change.':
        'Centraliza os dados atuais automaticamente sem alterar a escala deste eixo.',
    'Display averages of the curves displayed in this plot. The parameter list allows you to choose parameters to average over (if any are available).':
        'Mostra a média das curvas. A lista permite escolher os parâmetros do agrupamento, quando disponíveis.',
    'Plot only the portion of each curve that is visible. This assumes X values are uniformly spaced.':
        'Desenha apenas a parte visível de cada curva. Pressupõe valores X igualmente espaçados.',
    'If multiple curves are displayed in this plot, check this box to limit the number of traces that are displayed.':
        'Limita a quantidade de curvas exibidas neste gráfico.',
    'Downsample by drawing a saw wave that follows the min and max of the original data. This method produces the best visual representation of the data but is slower.':
        'Reduz os pontos preservando os mínimos e máximos. Representa melhor os picos, mas exige mais processamento.',
    'If multiple curves are displayed in this plot, check "Max Traces" and set this value to limit the number of traces that are displayed.':
        'Ative Máximo de curvas e informe a quantidade de curvas que podem aparecer.',
    'If MaxTraces is checked, remove curves from memory after they are hidden (saves memory, but traces can not be un-hidden).':
        'Com Máximo de curvas ativo, remove da memória as curvas ocultas. Economiza memória, mas impede reexibi-las.',
    'Downsample by taking the mean of N samples.': 'Reduz os pontos calculando a média de cada grupo de N amostras.',
    'Downsample by taking the first of N samples. This method is fastest and least accurate.':
        'Usa a primeira de cada grupo de N amostras. É mais rápido e menos preciso.',
    'Automatically downsample data based on the visible range. This assumes X values are uniformly spaced.':
        'Reduz os pontos automaticamente conforme a área visível. Pressupõe valores X igualmente espaçados.',
    'Downsample data before plotting. (plot every Nth sample)':
        'Reduz os dados antes de desenhar, usando uma amostra a cada N.',
}


class GraphTranslator(QTranslator):
    def isEmpty(self):
        return False

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if context not in ('ViewBox', 'Form', 'PlotItem', 'GraphicsScene', 'Exporter'):
            return None
        if sourceText in GRAPH_TEXT:
            return GRAPH_TEXT[sourceText]
        prefix, suffix = '<html><head/><body><p>', '</p></body></html>'
        text = sourceText.removeprefix(prefix).removesuffix(suffix)
        if text in GRAPH_HELP:
            return GRAPH_HELP[text]
        return None


def install_translations():
    app = QApplication.instance()
    if app is None or hasattr(app, '_medemax_translators'):
        return
    QLocale.setDefault(QLocale('pt_BR'))
    # Use Qt dialogs on every OS so their language does not depend on Windows.
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
    qt = QTranslator(app)
    path = asset_path('qtbase_pt_BR.qm')
    if not qt.load(str(path) if path else 'qtbase_pt_BR', QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        raise RuntimeError('Tradução do Qt não encontrada: qtbase_pt_BR.qm')
    graph = GraphTranslator(app)
    app.installTranslator(qt)
    app.installTranslator(graph)
    app._medemax_translators = (qt, graph)


def status_text(value):
    return {'Online': 'Conectado', 'Offline': 'Sem comunicação', 'offline': 'Sem comunicação',
            'Timeout': 'Tempo de resposta excedido', 'timeout': 'Tempo de resposta excedido'}.get(value, value)


def localize_plot(plot):
    """Handle pyqtgraph labels that are constructed without Qt's translate()."""
    menu = plot.getPlotItem().getViewBox().menu
    menu.actions()[1].setText('Eixo X')
    menu.actions()[2].setText('Eixo Y')
    menu.dv.setLocale(QLocale.c())  # pyqtgraph parses these range fields with float().
    for action in menu.actions()[1:3]:
        for widget_action in action.menu().actions():
            widget = widget_action.defaultWidget()
            widget.setMaximumWidth(480)
    # Keep axis-link values intact: pyqtgraph uses their text to identify views.
    scene = plot.scene()
    scene.contextMenu[0].triggered.disconnect(scene.showExportDialog)
    scene.contextMenu[0].triggered.connect(lambda: show_export_dialog(scene))


def show_export_dialog(scene):
    if scene.exportDialog is None:
        from .plot_export import PortugueseExportDialog
        scene.exportDialog = PortugueseExportDialog(scene)
    scene.exportDialog.show(getattr(scene, 'contextMenuItem', None))
