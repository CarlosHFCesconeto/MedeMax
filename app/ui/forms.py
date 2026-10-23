from dataclasses import fields, replace
from PySide6.QtWidgets import (QDialog,QFormLayout,QLineEdit,QComboBox,QCheckBox,QDialogButtonBox,QVBoxLayout,QScrollArea,QWidget,QMessageBox,QLabel)
from serial.tools import list_ports
from ..models import Device,Tag,AlarmRule,TYPES
from ..profiles import measurement_tags
from .language import install_translations

LABELS={'name':'Nome','description':'Descrição','transport':'Tipo de conexão','port':'Porta COM','baudrate':'Taxa de transmissão (baud)','parity':'Paridade','bytesize':'Bits de dados','stopbits':'Bits de parada','host':'Endereço IP ou nome de rede','tcp_port':'Porta TCP','unit_id':'Identificador Modbus (Slave / Unit ID)','timeout':'Tempo limite de resposta (s)','retries':'Novas tentativas de leitura','interval_ms':'Intervalo de consulta (ms)','enabled':'Ativo','device_id':'Dispositivo','function':'Função Modbus','address':'Endereço (base zero)','count':'Quantidade de registradores/bits','data_type':'Tipo de dado','byte_order':'Ordem dos bytes','word_order':'Ordem dos registradores','scale':'Escala','offset':'Ajuste adicional (offset)','unit':'Unidade','decimals':'Casas decimais','writable':'Permitir escrita','polling':'Consulta habilitada','history':'Histórico habilitado','write_min':'Mínimo de escrita (valor real)','write_max':'Máximo de escrita (valor real)','tag_id':'Tag','condition':'Condição','threshold':'Limite','severity':'Severidade','message':'Mensagem'}

TYPE_LABELS={'Boolean':'Lógico (0/1)', 'UINT16':'UINT16 • Inteiro sem sinal (16 bits)',
             'INT16':'INT16 • Inteiro com sinal (16 bits)', 'UINT32':'UINT32 • Inteiro sem sinal (32 bits)',
             'INT32':'INT32 • Inteiro com sinal (32 bits)', 'FLOAT32':'FLOAT32 • Ponto flutuante (32 bits)',
             'FLOAT64':'FLOAT64 • Ponto flutuante (64 bits)'}
ORDER_OPTIONS=[('Mais significativo primeiro (big-endian)','big'),('Menos significativo primeiro (little-endian)','little')]


class Editor(QDialog):
    def __init__(self,obj,core,parent=None):
        install_translations()
        super().__init__(parent)
        self.obj=obj; self.result_obj=None; self.inputs={}
        self.setWindowTitle('Configurar '+{Device:'dispositivo',Tag:'medição (tag)',AlarmRule:'regra de alarme'}[type(obj)])
        self.resize(780,690)
        layout=QVBoxLayout(self); scroll=QScrollArea(); scroll.setWidgetResizable(True)
        body=QWidget(); self.form=QFormLayout(body); scroll.setWidget(body); layout.addWidget(scroll)
        options={'transport':[('Modbus RTU','RTU'),('Modbus TCP','TCP'),('Simulação','SIM')],
                 'parity':[('Nenhuma (N)','N'),('Par (E)','E'),('Ímpar (O)','O')], 'bytesize':[7,8], 'stopbits':[1,1.5,2],
                 'function':[("01 • Saídas digitais (Coils)",1),("02 • Entradas digitais",2),("03 • Registradores de retenção",3),("04 • Registradores de entrada",4)],
                 'data_type':[(TYPE_LABELS[key],key) for key in TYPES], 'byte_order':ORDER_OPTIONS, 'word_order':ORDER_OPTIONS,
                 'condition':['>','<','==',('Ativo','ativo'),('Inativo','inativo'),('Sem comunicação','offline')],
                 'severity':['Informação','Aviso','Alta','Crítica'], 'device_id':[(d.name,d.id) for d in core.devices.values()], 'tag_id':[(t.name,t.id) for t in core.tags.values()]}
        for field in fields(obj):
            key=field.name
            if key in ('id', 'measurement_profile'): continue
            value=getattr(obj,key)
            if key in options:
                widget=QComboBox()
                for option in options[key]:
                    label,data=option if isinstance(option,tuple) else (str(option),option)
                    widget.addItem(label,data)
                idx=widget.findData(value)
                if idx>=0: widget.setCurrentIndex(idx)
            elif isinstance(value,bool): widget=QCheckBox(); widget.setChecked(value)
            elif key=='port':
                widget=QComboBox(); widget.setEditable(True)
                widget.addItems([p.device for p in list_ports.comports()]); widget.setCurrentText(value)
            else: widget=QLineEdit(str(value))
            self.inputs[key]=widget; self.form.addRow('Leitura em blocos contíguos' if key=='read_blocks' else LABELS.get(key,key),widget)
        if isinstance(obj,Device):
            self.inputs['transport'].currentIndexChanged.connect(self.visibility); self.visibility()
        if isinstance(obj,Tag):
            self.inputs['data_type'].currentIndexChanged.connect(self.count_changed)
            self.inputs['count'].setReadOnly(True); self.count_changed()
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def count_changed(self): self.inputs['count'].setText(str(TYPES[self.inputs['data_type'].currentData()][1]))

    def visibility(self):
        transport=self.inputs['transport'].currentData()
        for key in ('port','baudrate','parity','bytesize','stopbits'): self.form.setRowVisible(self.inputs[key],transport=='RTU')
        for key in ('host','tcp_port'): self.form.setRowVisible(self.inputs[key],transport=='TCP')

    def save(self):
        try:
            values={}
            for key,w in self.inputs.items():
                old=getattr(self.obj,key)
                if isinstance(w,QCheckBox): value=w.isChecked()
                elif isinstance(w,QComboBox): value=w.currentText() if key=='port' else w.currentData()
                else:
                    text=w.text().strip()
                    value=float(text.replace(',','.')) if isinstance(old,float) or key in ('scale','offset','stopbits','timeout','threshold','write_min','write_max') else int(text) if isinstance(old,int) else text
                values[key]=value
            self.result_obj=replace(self.obj,**values); self.result_obj.validate(); self.accept()
        except Exception as e: QMessageBox.warning(self,'Configuração inválida',str(e))


class MeasurementMapDialog(QDialog):
    def __init__(self, device, parent=None):
        install_translations()
        super().__init__(parent)
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView
        self.setWindowTitle('Aplicar mapa de 26 variáveis'); self.resize(700,700)
        layout=QVBoxLayout(self)
        title=QLabel(f'Dispositivo: {device.name}'); title.setWordWrap(True); layout.addWidget(title)
        note=QLabel('FC04 • endereços 0–25 • um inteiro de 16 bits por variável.\n'
                    'Confirme o formato no firmware: UINT16 = sem sinal; INT16 = com sinal.\n'
                    'I4 aparece como Corrente 4; a tabela não identifica esse canal como neutro.\n'
                    'O mapa não altera COM/IP, identificador Modbus ou intervalo de consulta e não inicia a aquisição.')
        note.setWordWrap(True); layout.addWidget(note)
        form=QFormLayout(); self.power_type=QComboBox(); self.factor_type=QComboBox()
        for combo in (self.power_type,self.factor_type): combo.addItems(['UINT16','INT16'])
        form.addRow('Potência ativa/reativa',self.power_type); form.addRow('Fator de potência',self.factor_type)
        layout.addLayout(form)
        self.group_reads=QCheckBox('Ler os 26 registradores em uma requisição por ciclo'); self.group_reads.setChecked(True)
        layout.addWidget(self.group_reads)
        self.preview=QTableWidget(26,5); self.preview.setHorizontalHeaderLabels(['Endereço','Medição','Unidade','Formato','Escala'])
        self.preview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.preview.horizontalHeader().setStretchLastSection(True); layout.addWidget(self.preview)
        def refresh():
            for i,tag in enumerate(measurement_tags(device.id,self.power_type.currentText(),self.factor_type.currentText())):
                for j,value in enumerate([tag.address,tag.name,tag.unit,tag.data_type,tag.scale]):
                    self.preview.setItem(i,j,QTableWidgetItem(str(value)))
        self.power_type.currentIndexChanged.connect(refresh); self.factor_type.currentIndexChanged.connect(refresh); refresh()
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText('Aplicar mapa')
        buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
