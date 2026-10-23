"""Configurable device dashboards, with bounded live plots and persistent preferences."""
import hashlib
import html
import re
from collections import defaultdict
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QPushButton,QLabel,
    QScrollArea,QFrame,QGridLayout,QCheckBox,QDialog,QDialogButtonBox,QListWidget,
    QListWidgetItem,QLineEdit,QSizePolicy)
import pyqtgraph as pg
from .language import install_translations, localize_plot, status_text

MODES=['Por dispositivo','Todos no mesmo gráfico','Por unidade','Uma medição por gráfico']
STYLES=['Linhas','Degraus','Pontos','Área']

def tag_color(tag):
    hue=int(hashlib.sha256(tag.id.encode()).hexdigest()[:8],16)%360
    return QColor.fromHsv(hue,200,145)

def measurement_card(tag):
    match=re.fullmatch(r'(Tensão|Corrente)\s+L?([1234N])',tag.name,re.IGNORECASE)
    if not match: return None
    kind,phase=match.groups(); row=0 if kind.casefold()=='tensão' else 1
    phase=phase.upper(); column=3 if phase=='4' else ('1','2','3','N').index(phase)
    return row,column,f'{"Tensão" if row==0 else "Corrente"} {phase}'

class SelectionDialog(QDialog):
    def __init__(self,title,entries,selected,parent):
        install_translations()
        super().__init__(parent); self.setWindowTitle(title); self.resize(560,490)
        layout=QVBoxLayout(self); search=QLineEdit(); search.setPlaceholderText('Buscar pelo nome…'); layout.addWidget(search)
        self.items=QListWidget(); layout.addWidget(self.items)
        for identifier,name in entries:
            item=QListWidgetItem(name); item.setData(Qt.UserRole,identifier)
            item.setFlags(item.flags()|Qt.ItemIsUserCheckable); item.setCheckState(Qt.Checked if identifier in selected else Qt.Unchecked); self.items.addItem(item)
        search.textChanged.connect(lambda text:[self.items.item(i).setHidden(text.casefold() not in self.items.item(i).text().casefold()) for i in range(self.items.count())])
        row=QHBoxLayout(); layout.addLayout(row)
        for label,state in [('Selecionar todos',Qt.Checked),('Limpar seleção',Qt.Unchecked)]:
            btn=QPushButton(label); btn.clicked.connect(lambda checked=False,state=state:[self.items.item(i).setCheckState(state) for i in range(self.items.count())]); row.addWidget(btn)
        buttons=QDialogButtonBox(QDialogButtonBox.Apply|QDialogButtonBox.Cancel); layout.addWidget(buttons)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.accept); buttons.rejected.connect(self.reject)

    def selected(self):
        return [self.items.item(i).data(Qt.UserRole) for i in range(self.items.count()) if self.items.item(i).checkState()==Qt.Checked]

class Dashboard(QWidget):
    presentationRequested=Signal(bool)
    def __init__(self,core):
        install_translations()
        super().__init__(); self.core=core; self.focus=None; self.presentation=False; self.chart_controls=[]; self.curves={}; self.plots=[]; self.values={}; self.status={}
        self.styles=core.repo.setting('dashboard_chart_styles',{})
        self.setStyleSheet('QLabel,QCheckBox{background:transparent;} QFrame#panel{background:white;border:1px solid #dce3eb;border-radius:10px;} QLabel#heading{font-size:18px;font-weight:600;color:#183b62;} QLabel#muted{color:#64748b;}')
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(12)
        nav=QHBoxLayout(); layout.addLayout(nav)
        self.back=QPushButton('← Visão geral'); self.back.clicked.connect(lambda:self.open_device(None)); nav.addWidget(self.back)
        self.breadcrumb=QLabel('Visão geral'); self.breadcrumb.setObjectName('heading'); nav.addWidget(self.breadcrumb); nav.addStretch()
        self.devices_btn=QPushButton('Dispositivos'); self.devices_btn.clicked.connect(self.choose_devices); nav.addWidget(self.devices_btn)
        self.tags_btn=QPushButton('Medições'); self.tags_btn.clicked.connect(self.choose_tags); nav.addWidget(self.tags_btn)
        self.options_btn=QPushButton('Opções'); self.options_btn.setVisible(False); self.options_btn.clicked.connect(self.toggle_options); nav.addWidget(self.options_btn)
        self.present_btn=QPushButton('Apresentação • F11'); self.present_btn.clicked.connect(lambda:self.presentationRequested.emit(not self.presentation)); nav.addWidget(self.present_btn)
        toolbar=QFrame(); self.toolbar=toolbar; toolbar.setObjectName('panel'); row=QHBoxLayout(toolbar); layout.addWidget(toolbar)
        self.mode=QComboBox(); self.mode.addItems(MODES); self.mode.setCurrentIndex(core.repo.setting('dashboard_mode',0))
        self.quantity=QComboBox()
        self.window=QComboBox()
        for label,n in [('1 minuto',60),('5 minutos',300),('15 minutos',900),('1 hora',3600),('6 horas',21600),('24 horas',86400)]: self.window.addItem(label,n)
        idx=self.window.findData(core.repo.setting('dashboard_window',60)); self.window.setCurrentIndex(max(0,idx))
        for label,w in [('Organizar',self.mode),('Unidade',self.quantity),('Janela',self.window)]: row.addWidget(QLabel(label)); row.addWidget(w)
        row.addStretch(); self.auto=QCheckBox('Eixos automáticos'); self.auto.setChecked(True); row.addWidget(self.auto)
        self.pause=QCheckBox('Pausar gráficos'); row.addWidget(self.pause)
        self.summary=QLabel(); self.summary.setObjectName('muted'); layout.addWidget(self.summary)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame); layout.addWidget(scroll)
        self.body=QWidget(); self.body_layout=QVBoxLayout(self.body); self.body_layout.setContentsMargins(0,0,0,0); self.body_layout.setSpacing(14); scroll.setWidget(self.body)
        self.mode.currentIndexChanged.connect(self.changed); self.quantity.currentIndexChanged.connect(self.rebuild)
        self.window.currentIndexChanged.connect(lambda:self.core.repo.set_setting('dashboard_window',self.window.currentData()))
        self.auto.toggled.connect(self.auto_changed)

    def set_presentation(self,enabled):
        self.presentation=enabled; self.toolbar.setVisible(not enabled); self.summary.setVisible(not enabled)
        self.options_btn.setVisible(enabled); self.present_btn.setText('Sair • Esc' if enabled else 'Apresentação • F11')
        self.rebuild()

    def toggle_options(self):
        self.toolbar.setVisible(not self.toolbar.isVisible())
        for widget in self.chart_controls: widget.setVisible(self.toolbar.isVisible())

    def selected_devices(self):
        saved=self.core.repo.setting('dashboard_devices',None)
        return set(self.core.devices if saved is None else saved)

    def selected_tags(self):
        saved=self.core.repo.setting('dashboard_measurements',None)
        return set(self.core.tags if saved is None else saved)

    def choose_devices(self):
        dialog=SelectionDialog('Dispositivos no Dashbord',[(d.id,d.name) for d in self.core.devices.values()],self.selected_devices(),self)
        if dialog.exec():
            self.set_devices(dialog.selected())

    def set_devices(self,identifiers):
        self.core.repo.set_setting('dashboard_devices',list(identifiers)); self.focus=None; self.rebuild()

    def choose_tags(self):
        ids={self.focus} if self.focus else self.selected_devices()
        entries=[(t.id,f'{self.core.devices[t.device_id].name} • {t.name} [{t.unit or "sem unidade"}]') for t in self.core.tags.values() if t.device_id in ids]
        dialog=SelectionDialog('Medições no Dashbord',entries,self.selected_tags(),self)
        if dialog.exec():
            untouched=self.selected_tags()-{identifier for identifier,_ in entries}
            self.core.repo.set_setting('dashboard_measurements',list(untouched|set(dialog.selected()))); self.rebuild()

    def changed(self):
        self.core.repo.set_setting('dashboard_mode',self.mode.currentIndex()); self.rebuild()

    def auto_changed(self,checked):
        for p in self.plots: p.enableAutoRange(x=checked,y=checked)

    def open_device(self,identifier):
        self.focus=identifier; self.rebuild()

    def panel(self,title):
        box=QFrame(); box.setObjectName('panel'); layout=QVBoxLayout(box); layout.setContentsMargins(16,14,16,14)
        header=QHBoxLayout(); label=QLabel(title); label.setObjectName('heading'); header.addWidget(label); header.addStretch(); layout.addLayout(header)
        return box,layout,header

    def style_changed(self,key,combo,curves):
        style=combo.currentIndex(); self.styles[key]=style; self.core.repo.set_setting('dashboard_chart_styles',self.styles)
        for identifier,curve in curves.items():
            color=tag_color(self.core.tags[identifier]); brush=QColor(color); brush.setAlpha(32)
            curve.setPen(None if style==2 else pg.mkPen(color,width=2))
            curve.setSymbol('o' if style==2 else None); curve.setSymbolSize(5); curve.setSymbolBrush(color); curve.setSymbolPen(None)
            curve.setFillLevel(0 if style==3 else None); curve.setBrush(brush if style==3 else None)
            curve.opts['stepMode']='left' if style==1 else None
        self.refresh()

    def add_plot(self,parent_layout,title,tags,key,device=None):
        box,v,header=self.panel(title); parent_layout.addWidget(box)
        style=QComboBox(); style.addItems(STYLES); style.setCurrentIndex(self.styles.get(key,0)); header.addWidget(style)
        reset=QPushButton('Ajustar eixos'); header.addWidget(reset)
        self.chart_controls.extend([style,reset]); style.setVisible(not self.presentation or self.toolbar.isVisible()); reset.setVisible(not self.presentation or self.toolbar.isVisible())
        plot=pg.PlotWidget(axisItems={'bottom':pg.DateAxisItem()}); localize_plot(plot); plot.setBackground('w'); plot.showGrid(x=True,y=True,alpha=.12); plot.setFixedHeight(270)
        units={t.unit or 'sem unidade' for t in tags}; plot.setLabel('left',next(iter(units)) if len(units)==1 else 'Valores • unidades diferentes',color='#475569'); plot.setLabel('bottom','Horário',color='#475569')
        for axis in ('left','bottom'): plot.getAxis(axis).setTextPen('#475569'); plot.getAxis(axis).setPen('#cbd5e1')
        plot.setClipToView(True); v.addWidget(plot); self.plots.append(plot); reset.clicked.connect(lambda:plot.autoRange())
        if device: plot.scene().sigMouseClicked.connect(lambda event,d=device:self.open_device(d) if event.double() else None)
        if len(units)>1:
            note=QLabel('Unidades diferentes compartilham o eixo. Use “Por unidade” para comparar amplitudes.'); note.setWordWrap(True); note.setObjectName('muted'); v.addWidget(note)
        legend=QGridLayout(); v.addLayout(legend); curves={}
        for i,t in enumerate(tags):
            name=f'{self.core.devices[t.device_id].name} • {t.name} [{t.unit or "sem unidade"}]'
            curve=plot.plot([],[],name=name,connect='finite'); self.curves[t.id]=curve; curves[t.id]=curve
            check=QCheckBox(name); check.setChecked(True); check.setToolTip('Mostrar ou ocultar esta série neste gráfico'); check.setStyleSheet(f'color:{tag_color(t).name()};font-size:11px;'); check.toggled.connect(curve.setVisible); legend.addWidget(check,i//2,i%2)
        style.currentIndexChanged.connect(lambda:self.style_changed(key,style,curves)); self.style_changed(key,style,curves)
        plot.enableAutoRange(x=self.auto.isChecked(),y=self.auto.isChecked())

    def rebuild(self):
        if self.focus not in self.core.devices: self.focus=None
        current=self.quantity.currentData(); self.quantity.blockSignals(True); self.quantity.clear(); self.quantity.addItem('Todas',None)
        for unit in sorted({t.unit for t in self.core.tags.values() if t.unit}): self.quantity.addItem(unit,unit)
        self.quantity.setCurrentIndex(max(0,self.quantity.findData(current))); self.quantity.blockSignals(False)
        self.back.setVisible(self.focus is not None)
        self.breadcrumb.setText('Visão geral' if self.focus is None else 'Visão geral / '+self.core.devices[self.focus].name)
        while self.body_layout.count():
            item=self.body_layout.takeAt(0)
            if item.widget(): item.widget().hide(); item.widget().deleteLater()
        self.curves={}; self.plots=[]; self.values={}; self.status={}; self.chart_controls=[]
        devices=[d for d in self.core.devices.values() if d.id==self.focus] if self.focus else [d for d in self.core.devices.values() if d.id in self.selected_devices()]
        ids={d.id for d in devices}; selection=self.selected_tags(); unit=self.quantity.currentData()
        tags=[t for t in self.core.tags.values() if t.device_id in ids and t.enabled and t.id in selection and (unit is None or t.unit==unit)]
        self.devices_btn.setText(f'Dispositivos ({len(self.selected_devices()&set(self.core.devices))}/{len(self.core.devices)})')
        self.summary.setText(f'{len(devices)} dispositivos • {len(tags)} medições visíveis • Clique em “Abrir painel” para detalhar. A seleção altera apenas a visualização.')
        summaries=QWidget(); grid=QGridLayout(summaries); grid.setContentsMargins(0,0,0,0); self.body_layout.addWidget(summaries)
        for i,d in enumerate(devices):
            box,v,header=self.panel(d.name); label=QLabel('Sem leitura'); label.setObjectName('muted'); v.addWidget(label); self.status[d.id]=label
            if self.presentation and not self.focus:
                measurements=QGridLayout(); v.addLayout(measurements)
                for j,t in enumerate(t for t in tags if t.device_id==d.id):
                    label=QLabel(); label.setTextFormat(Qt.PlainText); label.setStyleSheet('font-size:14px;color:#194785;'); measurements.addWidget(label,j//2,j%2); self.values[t.id]=label
            btn=QPushButton('Abrir painel'); btn.clicked.connect(lambda checked=False,identifier=d.id:self.open_device(identifier)); v.addWidget(btn); btn.setVisible(self.focus is None); grid.addWidget(box,i//3,i%3)
        summaries.setVisible(not(self.presentation and self.focus))
        if self.focus:
            cards=QWidget(); g=QGridLayout(cards); g.setContentsMargins(0,0,0,0); self.body_layout.addWidget(cards)
            extra=0; occupied=set()
            for t in tags:
                spec=measurement_card(t)
                if spec and spec[:2] not in occupied:
                    row,column,title=spec; occupied.add((row,column))
                else:
                    row,column,title=2+extra//4,extra%4,t.name; extra+=1
                box,v,_=self.panel(title); label=QLabel('—'); label.setStyleSheet('font-size:23px;font-weight:600;color:#194785;'); label.setTextFormat(Qt.RichText); v.addWidget(label); self.values[t.id]=label; g.addWidget(box,row,column)
        mode=self.mode.currentIndex(); groups=defaultdict(list)
        for t in tags:
            group=t.device_id if mode==0 else 'all' if mode==1 else (t.unit or 'sem unidade') if mode==2 else t.id
            groups[group].append(t)
        for group,entries in groups.items():
            title=self.core.devices[group].name if mode==0 else 'Comparação dos dispositivos' if mode==1 else f'Medições em {group}' if mode==2 else f'{self.core.devices[entries[0].device_id].name} • {entries[0].name}'
            self.add_plot(self.body_layout,title,entries,f'{mode}:{group}',group if mode==0 and not self.focus else None)
        if not tags:
            empty=QLabel('Nenhuma medição selecionada. Use Dispositivos, Medições ou altere o filtro de unidade.'); empty.setWordWrap(True); self.body_layout.addWidget(empty)
        self.body_layout.addStretch(); self.refresh()

    def refresh(self):
        latest,status=self.core.snapshot()
        for identifier,label in self.status.items():
            s=status.get(identifier,{})
            state=status_text(s.get('state','Sem leitura')) if self.core.running else 'Parado'
            label.setText(state if self.presentation else f"{state} • {s.get('average_ms',0):.1f} ms por leitura • {s.get('errors',0)} erros")
        for identifier,label in self.values.items():
            t=self.core.tags[identifier]; s=latest.get(identifier)
            value=(f'{s.value:.{t.decimals}f}'.replace('.',',')+f' {t.unit}' if s and s.quality=='OK' else '—')
            quality=status_text(s.quality) if s else 'Sem leitura'
            if self.presentation and not self.focus:
                name=measurement_card(t)[2] if measurement_card(t) else t.name
                label.setText(f'{name}: {value}'+(' • '+quality if quality!='OK' else '')); continue
            label.setText(html.escape(value)+f'<br><span style="font-size:12px;font-weight:400;color:#64748b">{html.escape(quality)}</span>')
        if self.pause.isChecked(): return
        for identifier,curve in self.curves.items():
            data=self.core.graph(identifier,self.window.currentData()); curve.setData([p[0] for p in data],[p[1] for p in data])
        if self.auto.isChecked():
            for p in self.plots: p.enableAutoRange(x=True,y=True)
