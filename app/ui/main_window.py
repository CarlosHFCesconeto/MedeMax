from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import queue
import threading
import time
from PySide6.QtCore import Qt,QTimer,QDateTime
from PySide6.QtGui import QIcon,QShortcut,QKeySequence
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QListWidget,QListWidgetItem,QStackedWidget,QTableWidget,QTableWidgetItem,QHeaderView,QComboBox,QCheckBox,QSpinBox,QDateTimeEdit,QFileDialog,QMessageBox,QInputDialog,QPlainTextEdit,QGroupBox,QScrollArea)
import pyqtgraph as pg
from ..models import Device,Tag,AlarmRule
from ..services.core import scan
from .forms import Editor, MeasurementMapDialog
from .about import AboutPage
from .dashboard import Dashboard
from .language import install_translations, localize_plot, status_text
from .branding import asset_path, logo


PALETTE=['#2563eb','#c2410c','#087f5b','#7c3aed','#be185d','#0369a1']

def stamp(ts): return datetime.fromtimestamp(ts).strftime('%d/%m %H:%M:%S') if ts else '—'
def button(text,fn,layout):
    w=QPushButton(text); w.clicked.connect(fn); layout.addWidget(w); return w

def table(headers):
    w=QTableWidget(0,len(headers)); w.setHorizontalHeaderLabels(headers)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    w.horizontalHeader().setStretchLastSection(True)
    w.setSelectionBehavior(QTableWidget.SelectRows); w.setSelectionMode(QTableWidget.SingleSelection)
    w.setEditTriggers(QTableWidget.NoEditTriggers); w.verticalHeader().hide(); return w

def cell(t,row,col,value):
    value=("Sim" if value else "Não") if isinstance(value,bool) else str(value)
    item=t.item(row,col)
    if item is None: t.setItem(row,col,QTableWidgetItem(value))
    elif item.text()!=value: item.setText(value)


class MainWindow(QMainWindow):
    def __init__(self,core):
        install_translations()
        super().__init__(); self.core=core; self.executor=ThreadPoolExecutor(max_workers=2)
        self.presentation=False; self.presentation_geometry=None; self.presentation_state=None; self.presentation_page=0
        self.pending=[]; self.scan_cancel=threading.Event(); self.scan_queue=queue.Queue(maxsize=512)
        self.scan_future=None; self.closing=False; self.last_alarm_refresh=0
        self.setWindowTitle('MedeMax v0.3.6 • Supervisório Modbus'); self.resize(1360,850)
        project_logo = asset_path('medemax.png')
        if project_logo: self.setWindowIcon(QIcon(str(project_logo)))
        self.setStyleSheet('''QMainWindow,QWidget {background:#f3f6fa;color:#1e293b;font-size:13px;} QGroupBox{background:white;border:1px solid #dce3eb;border-radius:8px;margin-top:12px;padding:16px;} QGroupBox::title{subcontrol-origin:margin;left:15px;} QPushButton{background:#e0eafa;border:1px solid #c4d4ed;border-radius:5px;padding:8px 13px;} QPushButton:hover{background:#cbdcf5;} QPushButton:disabled{color:#8a96a6;} QLineEdit,QComboBox,QSpinBox,QDateTimeEdit{background:white;border:1px solid #cbd5e1;padding:6px;border-radius:4px;} QTableWidget,QListWidget,QPlainTextEdit{background:white;border:1px solid #dce3eb;} QHeaderView::section{background:#eaf0f7;padding:8px;border:0;} QListWidget::item{padding:10px;} QListWidget::item:selected{background:#d8e8ff;color:#17458f;}''')
        central=QWidget(); self.setCentralWidget(central); outer=QVBoxLayout(central)
        self.header=QWidget(); top=QHBoxLayout(self.header); top.setContentsMargins(0,0,0,0); top.addWidget(logo('medemax.png',56,56,'MedeMax')); title=QLabel('MedeMax'); title.setStyleSheet('font-size:22px;font-weight:700;color:#194785'); top.addWidget(title); top.addStretch()
        self.start_btn=button('Iniciar aquisição',self.start,top); self.stop_btn=button('Parar',self.stop,top)
        button('Criar demonstração',self.demo,top); button('Simular 3 medidores',self.demo_multi,top); outer.addWidget(self.header)
        body=QHBoxLayout(); self.nav=QListWidget(); self.nav.setFixedWidth(185)
        self.stack=QStackedWidget(); body.addWidget(self.nav); body.addWidget(self.stack,1); outer.addLayout(body,1)
        self.footer=QLabel(); outer.addWidget(self.footer)
        self.pages={}
        self.build_dashboard(); self.build_watch(); self.build_history(); self.build_alarms()
        self.build_config('Dispositivos',Device); self.build_config('Tags',Tag); self.build_diagnostics(); self.build_settings()
        about = AboutPage(); self.pages['Sobre'] = about; self.nav.addItem('Sobre'); self.stack.addWidget(about)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex); self.nav.setCurrentRow(0)
        self.device_dashboard.presentationRequested.connect(self.set_presentation)
        self.fullscreen_shortcut=QShortcut(QKeySequence('F11'),self); self.fullscreen_shortcut.activated.connect(lambda:self.set_presentation(not self.presentation))
        self.escape_shortcut=QShortcut(QKeySequence('Escape'),self); self.escape_shortcut.activated.connect(lambda:self.set_presentation(False)); self.escape_shortcut.setEnabled(False)
        self.refresh_config(); self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(200)

    def set_presentation(self,enabled):
        if enabled==self.presentation: return
        if enabled:
            self.presentation_geometry=self.saveGeometry(); self.presentation_state=self.windowState(); self.presentation_page=self.nav.currentRow()
            self.nav.setCurrentRow(0)
        self.presentation=enabled
        self.header.setVisible(not enabled); self.nav.setVisible(not enabled); self.footer.setVisible(not enabled)
        self.pages['Dashboard'].layout().itemAt(0).widget().setVisible(not enabled)
        self.device_dashboard.set_presentation(enabled); self.escape_shortcut.setEnabled(enabled)
        if enabled: self.showFullScreen()
        else:
            self.setWindowState(self.presentation_state); self.restoreGeometry(self.presentation_geometry); self.show(); self.nav.setCurrentRow(self.presentation_page)

    def page(self,name,title=None):
        title=title or name
        w=QWidget(); layout=QVBoxLayout(w); label=QLabel(title); label.setStyleSheet('font-size:25px;font-weight:600'); layout.addWidget(label)
        self.nav.addItem(title); self.stack.addWidget(w); self.pages[name]=w; return layout

    def guard(self,fn):
        try: return fn()
        except Exception as e: QMessageBox.warning(self,'Não foi possível concluir',str(e))

    def async_task(self,fn,done):
        self.pending.append((self.executor.submit(fn),done))

    def start(self):
        if self.scan_future and not self.scan_future.done(): QMessageBox.warning(self,'Busca de registradores ativa','Aguarde ou cancele a busca de registradores.'); return
        self.guard(self.core.start)

    def stop(self):
        self.core.request_stop()
        self.async_task(lambda:self.core.stop(),lambda ok:None)

    def demo(self): self.guard(self.core.demo); self.refresh_config()

    def demo_multi(self):
        self.guard(self.core.demo_multi); self.refresh_config()

    def build_dashboard(self):
        layout=self.page('Dashboard','Dashbord'); self.device_dashboard=Dashboard(self.core); layout.addWidget(self.device_dashboard)

    def build_watch(self):
        layout=self.page('Monitoramento'); controls=QHBoxLayout()
        self.window_combo=QComboBox()
        for label,value in [('1 minuto',60),('5 minutos',300),('15 minutos',900),('1 hora',3600),('6 horas',21600),('12 horas',43200),('24 horas',86400)]: self.window_combo.addItem(label,value)
        controls.addWidget(QLabel('Janela')); controls.addWidget(self.window_combo)
        self.auto_axes=QCheckBox('Eixos X/Y automáticos'); self.auto_axes.setChecked(True); controls.addWidget(self.auto_axes)
        self.pause=QCheckBox('Pausar gráfico'); controls.addWidget(self.pause)
        button('Limpar gráfico',self.clear_graph,controls); self.write_btn=button('Escrever na tag selecionada',self.write_tag,controls)
        layout.addLayout(controls)
        self.watch=table(['Tag','Valor','Unidade','Qualidade','Última atualização','Dispositivo','Bruto / hexadecimal (HEX)']); layout.addWidget(self.watch,2)
        self.series=QListWidget(); self.series.setMaximumHeight(115); self.series.itemChanged.connect(self.series_changed); layout.addWidget(self.series)
        self.plot=pg.PlotWidget(axisItems={'bottom':pg.DateAxisItem()}); localize_plot(self.plot); self.plot.setBackground('w'); self.plot.addLegend(); self.plot.showGrid(x=True,y=True,alpha=.15); layout.addWidget(self.plot,3)
        self.curves={}; self.dashboard_curves={}

    def selected_tags(self): return [self.series.item(i).data(Qt.UserRole) for i in range(self.series.count()) if self.series.item(i).checkState()==Qt.Checked]

    def series_changed(self):
        selected=self.selected_tags(); self.core.repo.set_setting('dashboard_tags',selected)
        self.plot.clear(); self.curves.clear()
        for i,identifier in enumerate(selected):
            self.curves[identifier]=self.plot.plot([],[],name=f"{self.core.devices[self.core.tags[identifier].device_id].name} • {self.core.tags[identifier].name} [{self.core.tags[identifier].unit}]",pen=pg.mkPen(PALETTE[i%len(PALETTE)],width=2),connect='finite')
        self.device_dashboard.rebuild()

    def clear_graph(self):
        with self.core.lock: self.core.buffers.clear()
        for curve in list(self.curves.values())+list(self.dashboard_curves.values()): curve.setData([],[])

    def write_tag(self):
        row=self.watch.currentRow()
        if row<0: return
        tag=list(self.core.tags.values())[row]
        if not tag.writable: QMessageBox.warning(self,'Somente leitura','Habilite a escrita e configure seus limites na tag.'); return
        value,ok=QInputDialog.getText(self,'Escrever valor',f'{tag.name} ({tag.unit})\nNovo valor real; Lógico: 0 ou 1')
        if not ok: return
        try: number=float(value.replace(',','.'))
        except ValueError: QMessageBox.warning(self,'Valor inválido','Informe um número.'); return
        sample=self.core.latest.get(tag.id); d=self.core.devices[tag.device_id]
        msg=f'Dispositivo: {d.name}\nTag: {tag.name}\nEndereço: {tag.address} • ID Modbus {d.unit_id}\nAtual: {sample.value if sample else "—"} {tag.unit}\nNovo: {number} {tag.unit}\n\nEnviar uma única vez?'
        if QMessageBox.question(self,'Confirmar comando',msg,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return
        future=self.guard(lambda:self.core.write(tag.id,number))
        if future:
            self.write_btn.setEnabled(False)
            def complete(result):
                self.write_btn.setEnabled(True); QMessageBox.information(self,'Resultado da escrita',result[0]+'\n'+result[1]+('\nVerifique o valor no equipamento antes de tentar novamente.' if result[0]=='Indeterminado' else ''))
            self.pending.append((future,complete))

    def build_history(self):
        layout=self.page('Histórico'); controls=QHBoxLayout(); self.preset=QComboBox(); self.preset.addItems(['Últimos 5 minutos','Última hora','Hoje','Últimas 24 horas','Últimos 7 dias','Último mês','Personalizado']); controls.addWidget(self.preset)
        self.date_from=QDateTimeEdit(QDateTime.currentDateTime().addSecs(-300)); self.date_to=QDateTimeEdit(QDateTime.currentDateTime())
        for w in (self.date_from,self.date_to): w.setCalendarPopup(True); w.setDisplayFormat('dd/MM/yyyy HH:mm:ss'); controls.addWidget(w)
        self.preset.currentIndexChanged.connect(self.history_dates); button('Consultar',self.query_history,controls); button('Exportar CSV',self.export_history,controls); layout.addLayout(controls)
        self.history_tags=QListWidget(); self.history_tags.setSelectionMode(QListWidget.MultiSelection); self.history_tags.setMaximumHeight(120); layout.addWidget(self.history_tags)
        self.history_label=QLabel('Selecione tags. Datas em horário local; banco e CSV em UTC.'); layout.addWidget(self.history_label)
        self.history_plot=pg.PlotWidget(axisItems={'bottom':pg.DateAxisItem()}); localize_plot(self.history_plot); self.history_plot.setBackground('w'); self.history_plot.addLegend(); layout.addWidget(self.history_plot,2)
        self.history_table=table(['Data/hora','Tag','Valor','Qualidade']); layout.addWidget(self.history_table,1)

    def history_dates(self):
        i=self.preset.currentIndex(); now=QDateTime.currentDateTime()
        if i==6: return
        start=now.addMonths(-1) if i==5 else now.addSecs(-[300,3600,0,86400,604800][i])
        if i==2: start=QDateTime(now.date(),__import__('PySide6.QtCore',fromlist=['QTime']).QTime(0,0))
        self.date_from.setDateTime(start); self.date_to.setDateTime(now)

    def history_args(self):
        if self.preset.currentIndex()!=6: self.history_dates()
        tags=[i.data(Qt.UserRole) for i in self.history_tags.selectedItems()]
        start=self.date_from.dateTime().toSecsSinceEpoch(); end=self.date_to.dateTime().toSecsSinceEpoch()
        if not tags or start>end: raise ValueError('Selecione tags e um período válido')
        return tags,start,end

    def query_history(self):
        args=self.guard(self.history_args)
        if args:
            self.history_label.setText('Consultando…')
            self.async_task(lambda:self.core.repo.history_overview(*args),self.show_history)

    def show_history(self,result):
        rows=result['rows']
        self.history_label.setText(f"{result['total']:,} amostras no período completo. Gráfico: mínimos/máximos por intervalo; tabela: últimas 500. CSV: dados completos.")
        self.history_plot.clear(); series={}
        for r in rows: series.setdefault(r['tag'],[]).append((r['ts'],r['value'] if r['quality']=='OK' else float('nan')))
        for i,(identifier,data) in enumerate(series.items()): self.history_plot.plot([v[0] for v in data],[v[1] for v in data],pen=pg.mkPen(PALETTE[i%len(PALETTE)],width=2),name=self.history_series_name(identifier),connect='finite')
        self.history_plot.enableAutoRange(x=True,y=True)
        shown=result['recent']; self.history_table.setRowCount(len(shown))
        for i,r in enumerate(shown):
            for j,value in enumerate([stamp(r['ts']),self.core.tags.get(r['tag'],Tag(name=r['tag'])).name,r['value'],status_text(r['quality'])]): cell(self.history_table,i,j,value)

    def history_series_name(self,identifier):
        tag=self.core.tags.get(identifier)
        if not tag: return identifier
        device=self.core.devices.get(tag.device_id)
        return f'{device.name if device else tag.device_id} • {tag.name} [{tag.unit}]'

    def export_history(self):
        args=self.guard(self.history_args)
        if not args: return
        path,_=QFileDialog.getSaveFileName(self,'Exportar CSV','historico.csv','CSV (*.csv)')
        if path: self.async_task(lambda:self.core.repo.export(path,*args),lambda n:QMessageBox.information(self,'CSV exportado',f'{n} amostras exportadas.'))

    def build_alarms(self):
        layout=self.page('Alarmes'); controls=QHBoxLayout(); self.active_only=QCheckBox('Somente ativos'); self.active_only.setChecked(True); controls.addWidget(self.active_only)
        button('Reconhecer selecionado',self.ack_alarm,controls); button('Nova regra',lambda:self.edit(AlarmRule),controls); button('Editar regra',self.edit_rule,controls); button('Excluir regra',self.remove_rule,controls); layout.addLayout(controls)
        self.rules_table=table(['Regra','Tag','Condição','Limite','Severidade','Ativa']); layout.addWidget(self.rules_table,1)
        self.alarm_table=table(['ID','Alarme','Severidade','Mensagem','Ativação','Valor','Reconhecimento','Normalização / encerramento']); layout.addWidget(self.alarm_table,2)

    def ack_alarm(self):
        row=self.alarm_table.currentRow()
        if row>=0: self.guard(lambda:self.core.repo.acknowledge(int(self.alarm_table.item(row,0).text()),time.time())); self.last_alarm_refresh=0

    def edit_rule(self):
        row=self.rules_table.currentRow()
        if row>=0: self.edit(AlarmRule,self.core.rules[row])

    def remove_rule(self):
        row=self.rules_table.currentRow()
        if row>=0: self.delete(AlarmRule,self.core.rules[row])

    def build_config(self,name,cls):
        layout=self.page(name); controls=QHBoxLayout(); button('Adicionar',lambda:self.edit(cls),controls); button('Editar',lambda:self.edit_selected(cls),controls); button('Excluir',lambda:self.delete_selected(cls),controls); controls.addStretch(); controls.addWidget(QLabel('Pare a aquisição para editar')); layout.addLayout(controls)
        if cls is Device:
            mapping=QHBoxLayout()
            button('Aplicar mapa 26 variáveis',self.apply_measurement_map,mapping)
            button('Simular mapa 26 variáveis',self.demo_measurement_map,mapping)
            mapping.addStretch(); layout.addLayout(mapping)
        t=table(['Nome','Conexão / Dispositivo','Configuração','Ativo']); layout.addWidget(t)
        if cls is Device: self.devices_table=t
        else: self.tags_table=t

    def apply_measurement_map(self):
        if self.core.running or (self.core.writer and self.core.writer.is_alive()) or (self.scan_future and not self.scan_future.done()):
            QMessageBox.warning(self,'Aquisição ativa','Pare a aquisição e a busca de registradores antes de aplicar o mapa.'); return
        row=self.devices_table.currentRow()
        if row<0:
            QMessageBox.information(self,'Selecione o medidor','Cadastre um dispositivo e selecione sua linha para aplicar as 26 variáveis.'); return
        device=list(self.core.devices.values())[row]
        dialog=MeasurementMapDialog(device,self)
        if dialog.exec():
            try:
                added=self.core.apply_measurement_map(device.id,dialog.power_type.currentText(),dialog.factor_type.currentText(),dialog.group_reads.isChecked())
                self.refresh_config()
                QMessageBox.information(self,'Mapa aplicado',f'{added} novas variáveis cadastradas. As 26 medições estão prontas.\nConfira COM/IP e o identificador Modbus, depois clique em Iniciar aquisição.')
            except Exception as e: QMessageBox.warning(self,'Mapa não aplicado',str(e))

    def demo_measurement_map(self):
        if self.core.running or (self.scan_future and not self.scan_future.done()):
            QMessageBox.warning(self,'Aquisição ativa','Pare a aquisição e a busca de registradores antes de criar a simulação.'); return
        self.guard(self.core.demo_measurement_map); self.refresh_config()

    def edit_selected(self,cls):
        t=self.devices_table if cls is Device else self.tags_table; values=list(self.core.devices.values() if cls is Device else self.core.tags.values())
        if t.currentRow()>=0: self.edit(cls,values[t.currentRow()])

    def delete_selected(self,cls):
        t=self.devices_table if cls is Device else self.tags_table; values=list(self.core.devices.values() if cls is Device else self.core.tags.values())
        if t.currentRow()>=0: self.delete(cls,values[t.currentRow()])

    def delete(self,cls,obj):
        if cls is Device:
            if self.scan_future and not self.scan_future.done():
                QMessageBox.warning(self,'Busca em andamento','Aguarde ou cancele a busca antes de excluir o dispositivo.'); return
            try: plan=self.core.device_removal_plan(obj.id)
            except Exception as e:
                QMessageBox.warning(self,'Não foi possível excluir',str(e)); return
            message=(f'Excluir o dispositivo “{plan["name"]}”?\n\n'
                     f'Tags vinculadas: {len(plan["tag_ids"])}\n'
                     f'Regras de alarme vinculadas: {len(plan["rule_ids"])}\n'
                     f'Alarmes ativos: {plan["active_alarms"]}\n\n'
                     'O dispositivo, suas tags e suas regras serão excluídos juntos.\n'
                     'Alarmes ativos serão encerrados com motivo de exclusão.\n'
                     'Os registros de medições e eventos serão preservados no banco.\n'
                     'As medições excluídas deixam de aparecer na seleção de tags.')
            box=QMessageBox(self); box.setWindowTitle('Excluir dispositivo e vínculos')
            box.setIcon(QMessageBox.Warning); box.setText(message)
            delete_button=box.addButton('Excluir dispositivo',QMessageBox.DestructiveRole)
            cancel_button=box.addButton('Cancelar',QMessageBox.RejectRole)
            box.setDefaultButton(cancel_button); box.setEscapeButton(cancel_button); box.exec()
            if box.clickedButton()==delete_button:
                self.guard(lambda:self.core.remove(Device,obj.id,expected_dependencies=plan))
                self.refresh_config(); self.last_alarm_refresh=0
            return
        if QMessageBox.question(self,'Excluir configuração',f'Excluir {obj.name}? Histórico será preservado.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
            self.guard(lambda:self.core.remove(cls,obj.id)); self.refresh_config()

    def edit(self,cls,obj=None):
        if self.core.running or (self.scan_future and not self.scan_future.done()): QMessageBox.warning(self,'Aquisição ativa','Pare a aquisição e a busca de registradores antes de configurar.'); return
        dialog=Editor(obj or cls(),self.core,self)
        if dialog.exec(): self.guard(lambda:self.core.save(dialog.result_obj)); self.refresh_config()

    def refresh_config(self):
        self.devices_table.setRowCount(len(self.core.devices)); self.scan_device.clear()
        for i,d in enumerate(self.core.devices.values()):
            for j,v in enumerate([d.name,d.transport,f'{d.port} / {d.baudrate}' if d.transport=='RTU' else f'{d.host}:{d.tcp_port}' if d.transport=='TCP' else 'Mapa fictício',d.enabled]): cell(self.devices_table,i,j,v)
            self.scan_device.addItem(d.name,d.id)
        self.tags_table.setRowCount(len(self.core.tags)); self.watch.setRowCount(len(self.core.tags))
        self.series.blockSignals(True); self.series.clear(); self.history_tags.clear()
        selected=self.core.repo.setting('dashboard_tags',None)
        for i,t in enumerate(self.core.tags.values()):
            device=self.core.devices[t.device_id]
            for j,v in enumerate([t.name,device.name,f'FC{t.function:02} @{t.address} {t.data_type} ×{t.scale} +{t.offset}',t.enabled]): cell(self.tags_table,i,j,v)
            item=QListWidgetItem(t.name); item.setData(Qt.UserRole,t.id); item.setFlags(item.flags()|Qt.ItemIsUserCheckable); item.setCheckState(Qt.Checked if (t.id in selected if selected is not None else i<4) else Qt.Unchecked); self.series.addItem(item)
            item=QListWidgetItem(t.name); item.setData(Qt.UserRole,t.id); self.history_tags.addItem(item); item.setSelected(True)
        self.series.blockSignals(False); self.series_changed()
        self.rules_table.setRowCount(len(self.core.rules))
        for i,r in enumerate(self.core.rules):
            for j,v in enumerate([r.name,self.core.tags[r.tag_id].name,status_text(r.condition),r.threshold,r.severity,r.enabled]): cell(self.rules_table,i,j,v)

    def build_diagnostics(self):
        layout=self.page('Diagnóstico'); controls=QHBoxLayout(); self.trace_check=QCheckBox('Capturar recebimentos/envios (RX/TX)'); self.trace_check.toggled.connect(lambda checked:setattr(self.core,'trace_enabled',checked)); controls.addWidget(self.trace_check)
        controls.addWidget(QLabel('Simulação')); self.sim_mode=QComboBox()
        for label,mode in [('Normal','normal'),('Tempo de resposta excedido','timeout'),('Sem comunicação','offline'),('Alarme','alarme')]: self.sim_mode.addItem(label,mode)
        self.sim_mode.currentIndexChanged.connect(lambda:self.core.set_simulation(self.sim_mode.currentData())); controls.addWidget(self.sim_mode); layout.addLayout(controls)
        self.status_table=table(['Dispositivo','Estado','Última leitura OK','Média ms','Erros']); layout.addWidget(self.status_table)
        self.trace_view=QPlainTextEdit(); self.trace_view.setReadOnly(True); self.trace_view.setMaximumBlockCount(1000); layout.addWidget(self.trace_view)
        group=QGroupBox('Busca de registradores somente leitura • aquisição deve estar parada • máximo 512 endereços'); box=QVBoxLayout(group); line=QHBoxLayout(); self.scan_device=QComboBox(); line.addWidget(self.scan_device)
        self.scan_function=QComboBox()
        for i in range(1,5): self.scan_function.addItem(f'FC {i:02}',i)
        line.addWidget(self.scan_function); self.scan_start=QSpinBox(); self.scan_end=QSpinBox()
        for label,w in [('Início',self.scan_start),('Fim',self.scan_end)]: w.setRange(0,65535); line.addWidget(QLabel(label)); line.addWidget(w)
        self.scan_end.setValue(9); self.scan_btn=button('Buscar registradores',self.start_scan,line); button('Cancelar',self.scan_cancel.set,line); box.addLayout(line)
        self.scan_table=table(['Endereço','UINT16 / Lógico','Hexadecimal (HEX)','INT16','Resultado']); box.addWidget(self.scan_table); layout.addWidget(group)

    def start_scan(self):
        if self.core.running: QMessageBox.warning(self,'Aquisição ativa','Pare a aquisição antes de buscar registradores.'); return
        if self.scan_future and not self.scan_future.done(): return
        identifier=self.scan_device.currentData()
        if not identifier: return
        d=self.core.devices[identifier]; f=self.scan_function.currentData(); start=self.scan_start.value(); end=self.scan_end.value()
        if not 0<=end-start<512: QMessageBox.warning(self,'Faixa inválida','Informe de 1 a 512 endereços.'); return
        self.scan_cancel.clear(); self.scan_table.setRowCount(0); self.scan_btn.setEnabled(False)
        self.scan_future=self.executor.submit(scan,d,f,start,end,self.scan_cancel,lambda *args:self.scan_queue.put(args))
        self.pending.append((self.scan_future,lambda _:self.scan_btn.setEnabled(True)))

    def build_settings(self):
        layout=self.page('Configurações'); layout.addWidget(QLabel('Retenção do histórico (dias). Amostras antigas são removidas em lotes a cada minuto.'))
        self.retention=QSpinBox(); self.retention.setRange(1,3650); self.retention.setValue(self.core.repo.setting('retention_days',60)); layout.addWidget(self.retention)
        button('Salvar retenção',lambda:self.core.repo.set_setting('retention_days',self.retention.value()),layout)
        layout.addWidget(QLabel('Banco de dados: '+self.core.repo.path)); layout.addWidget(QLabel('Configurações e histórico persistem automaticamente.\nFeche o programa antes de copiar o banco para cópia de segurança.\nNenhum dispositivo real é iniciado automaticamente.')); layout.addStretch()

    def tick(self):
        for future,done in self.pending[:]:
            if future.done():
                self.pending.remove((future,done))
                try: done(future.result())
                except Exception as e:
                    self.scan_btn.setEnabled(True)
                    if not self.closing: QMessageBox.warning(self,'Operação falhou',str(e))
        latest,status=self.core.snapshot()
        self.start_btn.setEnabled(not self.core.running and not (self.core.writer and self.core.writer.is_alive()))
        self.stop_btn.setEnabled(self.core.running)
        for i,t in enumerate(self.core.tags.values()):
            s=latest.get(t.id); good=s and s.quality=='OK'
            value=('Ativo' if s.value else 'Inativo') if good and t.data_type=='Boolean' else f'{s.value:.{t.decimals}f}'.replace('.',',') if good else '—'
            quality=status_text(s.quality) if s else 'Sem leitura'
            if not self.core.running and s: quality='Parado • '+quality
            for j,v in enumerate([t.name,value,t.unit,quality,stamp(s.timestamp) if s else '—',self.core.devices[t.device_id].name, ' / '.join(f'{int(x)} (0x{int(x):04X})' for x in s.raw) if s else '']): cell(self.watch,i,j,v)
        self.status_table.setRowCount(len(self.core.devices))
        summary=[]
        for i,d in enumerate(self.core.devices.values()):
            s=status.get(d.id,{}); state=status_text(s.get('state','Sem leitura')) if self.core.running else 'Parado'
            summary.append(f'{d.name}: {state}')
            for j,v in enumerate([d.name,state,stamp(s.get('last')),f'{s.get("average_ms",0):.1f}',s.get('errors',0)]): cell(self.status_table,i,j,v)
        if self.stack.currentWidget()==self.pages['Dashboard']: self.device_dashboard.refresh()
        if not self.pause.isChecked() and self.stack.currentWidget() == self.pages['Monitoramento']:
            if self.auto_axes.isChecked():
                self.plot.enableAutoRange(x=True,y=True)
            for identifier,curve in self.curves.items():
                data=self.core.graph(identifier,self.window_combo.currentData())
                x=[p[0] for p in data]; y=[p[1] for p in data]; curve.setData(x,y)
        if self.trace_check.isChecked():
            with self.core.lock:
                traces=list(self.core.diagnostics); self.core.diagnostics.clear()
            for ts,device,direction,detail in traces: self.trace_view.appendPlainText(f'{stamp(ts)} {device} {direction} {detail}')
        while True:
            try: address,value,result=self.scan_queue.get_nowait()
            except queue.Empty: break
            row=self.scan_table.rowCount(); self.scan_table.insertRow(row)
            for j,v in enumerate([address,value if value is not None else '—',f'{int(value):04X}' if value is not None else '—',int(value)-65536 if value is not None and int(value)>=32768 else value,status_text(result)]): cell(self.scan_table,row,j,v)
        if not self.closing and self.stack.currentWidget()==self.pages['Alarmes'] and time.monotonic()-self.last_alarm_refresh>1:
            self.last_alarm_refresh=time.monotonic(); active=self.active_only.isChecked()
            self.async_task(lambda:self.core.repo.alarms(active),self.show_alarms)
        self.footer.setText(('Aquisição em andamento' if self.core.running else 'Aquisição parada')+f'  •  {len(self.core.tags)} tags  •  Histórico descartado: {self.core.dropped_history}'+('  •  Falha de banco: '+self.core.storage_error if self.core.storage_error else ''))
        if self.closing and not self.core.running and not (self.core.writer and self.core.writer.is_alive()) and not self.pending: self.close()

    def show_alarms(self,events):
        self.alarm_table.setRowCount(len(events))
        for i,e in enumerate(events):
            ending='Encerrado por exclusão • '+stamp(e['retired']) if e.get('retired') is not None and e['normalized'] is None else stamp(e['normalized'])
            for j,v in enumerate([e['id'],e['name'],e['severity'],e['message'],stamp(e['activated']),e['value'],stamp(e['acknowledged']),ending]): cell(self.alarm_table,i,j,v)

    def closeEvent(self,event):
        self.closing=True; self.centralWidget().setEnabled(False); self.scan_cancel.set(); self.core.request_stop()
        if self.core.running or (self.core.writer and self.core.writer.is_alive()) or self.pending:
            self.footer.setText('Encerrando comunicação e salvando dados…'); event.ignore(); return
        self.timer.stop(); self.executor.shutdown(wait=True); self.core.repo.close(); event.accept()
