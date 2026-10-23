import csv
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)
import pyqtgraph as pg
from serial.tools import list_ports
from pymodbus.client import ModbusSerialClient


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "modbus_monitor.db"


def as_signed_16(value: int) -> int:
    """Converte UINT16 (0..65535) para INT16 (-32768..32767)."""
    return value - 65536 if value >= 32768 else value


class Database:
    def __init__(self, path: Path):
        DATA_DIR.mkdir(exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def _init_db(self):
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS modbus_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    port TEXT NOT NULL,
                    slave_id INTEGER NOT NULL,
                    function_code INTEGER NOT NULL,
                    address INTEGER NOT NULL,
                    value_unsigned INTEGER NOT NULL,
                    value_signed INTEGER NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_modbus_readings_timestamp
                ON modbus_readings(timestamp)
                """
            )

    def insert_reading_batch(
        self,
        timestamp: str,
        port: str,
        slave_id: int,
        function_code: int,
        start_address: int,
        registers: list[int],
    ):
        rows = [
            (
                timestamp,
                port,
                slave_id,
                function_code,
                start_address + offset,
                int(value),
                as_signed_16(int(value)),
            )
            for offset, value in enumerate(registers)
        ]
        with self._lock, self._connect() as con:
            con.executemany(
                """
                INSERT INTO modbus_readings (
                    timestamp, port, slave_id, function_code,
                    address, value_unsigned, value_signed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def export_csv(self, destination: Path) -> int:
        with self._lock, self._connect() as con:
            cur = con.execute(
                """
                SELECT timestamp, port, slave_id, function_code,
                       address, value_unsigned, value_signed
                FROM modbus_readings
                ORDER BY id
                """
            )
            rows = cur.fetchall()

        with destination.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(
                [
                    "data_hora",
                    "porta",
                    "slave_id",
                    "funcao",
                    "endereco",
                    "valor_uint16",
                    "valor_int16",
                ]
            )
            writer.writerows(rows)
        return len(rows)


class ModbusPoller(QThread):
    data_received = Signal(str, list)
    connection_state = Signal(bool, str)
    error = Signal(str)

    def __init__(
        self,
        port: str,
        baudrate: int,
        parity: str,
        stopbits: int,
        bytesize: int,
        slave_id: int,
        function_code: int,
        start_address: int,
        count: int,
        interval_ms: int,
    ):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.slave_id = slave_id
        self.function_code = function_code
        self.start_address = start_address
        self.count = count
        self.interval_ms = interval_ms
        self._running = True
        self.client = None

    def stop(self):
        self._running = False

    def run(self):
        self.client = ModbusSerialClient(
            port=self.port,
            baudrate=self.baudrate,
            parity=self.parity,
            stopbits=self.stopbits,
            bytesize=self.bytesize,
            timeout=1.0,
            retries=1,
        )

        try:
            if not self.client.connect():
                self.connection_state.emit(
                    False,
                    f"Não foi possível abrir {self.port}. Verifique a porta e o conversor.",
                )
                return

            self.connection_state.emit(True, f"Conectado em {self.port}")

            while self._running:
                started = time.monotonic()
                try:
                    if self.function_code == 3:
                        result = self.client.read_holding_registers(
                            self.start_address,
                            count=self.count,
                            device_id=self.slave_id,
                        )
                    else:
                        result = self.client.read_input_registers(
                            self.start_address,
                            count=self.count,
                            device_id=self.slave_id,
                        )

                    if result.isError():
                        self.error.emit(f"Resposta Modbus de erro: {result}")
                    else:
                        timestamp = datetime.now().isoformat(
                            sep=" ", timespec="milliseconds"
                        )
                        self.data_received.emit(timestamp, list(result.registers))

                except Exception as exc:
                    self.error.emit(f"Falha na leitura: {exc}")

                elapsed_ms = (time.monotonic() - started) * 1000
                remaining_ms = max(0, self.interval_ms - elapsed_ms)
                # Dorme em passos curtos para desconectar rapidamente.
                end_time = time.monotonic() + remaining_ms / 1000
                while self._running and time.monotonic() < end_time:
                    time.sleep(max(0, min(0.05, end_time - time.monotonic())))

        finally:
            try:
                if self.client:
                    self.client.close()
            finally:
                self.connection_state.emit(False, "Desconectado")


class MainWindow(QMainWindow):
    MAX_GRAPH_POINTS = 600

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor Modbus RTU")
        self.resize(1180, 760)

        self.db = Database(DB_PATH)
        self.poller = None
        self.last_registers = []
        self.current_start_address = 0
        self.graph_address = None
        self.graph_x = []
        self.graph_y = []
        self.read_count = 0

        self._build_ui()
        self.refresh_ports()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        settings_group = QGroupBox("Comunicação Modbus RTU")
        settings_layout = QHBoxLayout(settings_group)

        left_form = QFormLayout()
        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Atualizar portas")
        port_line = QHBoxLayout()
        port_line.addWidget(self.port_combo, 1)
        port_line.addWidget(self.refresh_button)
        left_form.addRow("Porta COM:", port_line)

        self.baud_combo = QComboBox()
        common_baudrates = [
            300, 600, 1200, 2400, 4800, 9600,
            14400, 19200, 38400, 57600, 115200
        ]
        for baud in common_baudrates:
            self.baud_combo.addItem(str(baud), baud)
        self.baud_combo.setCurrentIndex(
            self.baud_combo.findData(9600)
        )
        left_form.addRow("Baud rate:", self.baud_combo)

        self.parity_combo = QComboBox()
        self.parity_combo.addItem("Nenhuma (N)", "N")
        self.parity_combo.addItem("Par (E)", "E")
        self.parity_combo.addItem("Ímpar (O)", "O")
        left_form.addRow("Paridade:", self.parity_combo)

        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItem("1", 1)
        self.stopbits_combo.addItem("2", 2)
        left_form.addRow("Stop bits:", self.stopbits_combo)

        self.bytesize_combo = QComboBox()
        self.bytesize_combo.addItem("8", 8)
        self.bytesize_combo.addItem("7", 7)
        left_form.addRow("Data bits:", self.bytesize_combo)

        right_form = QFormLayout()

        self.slave_spin = QSpinBox()
        self.slave_spin.setRange(1, 247)
        self.slave_spin.setValue(1)
        right_form.addRow("Slave ID:", self.slave_spin)

        self.function_combo = QComboBox()
        self.function_combo.addItem("03 - Holding Registers", 3)
        self.function_combo.addItem("04 - Input Registers", 4)
        right_form.addRow("Função:", self.function_combo)

        self.address_spin = QSpinBox()
        self.address_spin.setRange(0, 65535)
        self.address_spin.setValue(0)
        right_form.addRow("Endereço inicial:", self.address_spin)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 125)
        self.count_spin.setValue(10)
        right_form.addRow("Quantidade:", self.count_spin)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 60_000)
        self.interval_spin.setSingleStep(100)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")
        right_form.addRow("Intervalo:", self.interval_spin)

        settings_layout.addLayout(left_form, 1)
        settings_layout.addSpacing(30)
        settings_layout.addLayout(right_form, 1)
        main_layout.addWidget(settings_group)

        controls = QHBoxLayout()
        self.connect_button = QPushButton("Conectar")
        self.connect_button.setMinimumHeight(38)
        self.disconnect_button = QPushButton("Desconectar")
        self.disconnect_button.setMinimumHeight(38)
        self.disconnect_button.setEnabled(False)
        self.logging_checkbox = QCheckBox("Salvar leituras no SQLite")
        self.logging_checkbox.setChecked(True)
        self.export_button = QPushButton("Exportar CSV")
        self.clear_graph_button = QPushButton("Limpar gráfico")

        controls.addWidget(self.connect_button)
        controls.addWidget(self.disconnect_button)
        controls.addWidget(self.logging_checkbox)
        controls.addStretch()
        controls.addWidget(self.clear_graph_button)
        controls.addWidget(self.export_button)
        main_layout.addLayout(controls)

        content = QHBoxLayout()

        table_group = QGroupBox("Registradores recebidos")
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Endereço", "UINT16", "HEX", "INT16"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_layout.addWidget(self.table)
        content.addWidget(table_group, 1)

        graph_group = QGroupBox("Gráfico em tempo real")
        graph_layout = QVBoxLayout(graph_group)
        graph_header = QHBoxLayout()
        self.graph_label = QLabel("Selecione um registrador na tabela")
        self.graph_mode_combo = QComboBox()
        self.graph_mode_combo.addItem("UINT16", "unsigned")
        self.graph_mode_combo.addItem("INT16", "signed")
        graph_header.addWidget(self.graph_label)
        graph_header.addStretch()
        graph_header.addWidget(QLabel("Exibir como:"))
        graph_header.addWidget(self.graph_mode_combo)
        graph_layout.addLayout(graph_header)

        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setLabel("left", "Valor")
        self.plot.setLabel("bottom", "Amostras")
        self.curve = self.plot.plot([], [], pen=pg.mkPen(width=2))
        graph_layout.addWidget(self.plot)

        content.addWidget(graph_group, 2)
        main_layout.addLayout(content, 1)

        footer = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #9e9e9e; font-size: 18px;")
        self.status_label = QLabel("Desconectado")
        self.last_read_label = QLabel("Última leitura: —")
        self.counter_label = QLabel("Leituras: 0")
        self.db_label = QLabel(f"Banco: {DB_PATH.name}")

        footer.addWidget(self.status_dot)
        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(self.last_read_label)
        footer.addSpacing(15)
        footer.addWidget(self.counter_label)
        footer.addSpacing(15)
        footer.addWidget(self.db_label)
        main_layout.addLayout(footer)

        self.refresh_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.start_polling)
        self.disconnect_button.clicked.connect(self.stop_polling)
        self.export_button.clicked.connect(self.export_csv)
        self.clear_graph_button.clicked.connect(self.clear_graph)
        self.table.itemSelectionChanged.connect(self.select_graph_register)
        self.graph_mode_combo.currentIndexChanged.connect(self.rebuild_graph_value)

    def refresh_ports(self):
        selected = self.port_combo.currentData()
        self.port_combo.clear()
        ports = list(list_ports.comports())

        for port in ports:
            description = port.description or "Porta serial"
            self.port_combo.addItem(
                f"{port.device} — {description}",
                port.device,
            )

        if selected:
            index = self.port_combo.findData(selected)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

        if not ports:
            self.port_combo.addItem("Nenhuma porta encontrada", None)

    def set_settings_enabled(self, enabled: bool):
        widgets = [
            self.port_combo,
            self.refresh_button,
            self.baud_combo,
            self.parity_combo,
            self.stopbits_combo,
            self.bytesize_combo,
            self.slave_spin,
            self.function_combo,
            self.address_spin,
            self.count_spin,
            self.interval_spin,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)

    def start_polling(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(
                self,
                "Porta serial",
                "Nenhuma porta COM válida foi selecionada.",
            )
            return

        self.current_start_address = self.address_spin.value()

        self.poller = ModbusPoller(
            port=port,
            baudrate=self.baud_combo.currentData(),
            parity=self.parity_combo.currentData(),
            stopbits=self.stopbits_combo.currentData(),
            bytesize=self.bytesize_combo.currentData(),
            slave_id=self.slave_spin.value(),
            function_code=self.function_combo.currentData(),
            start_address=self.current_start_address,
            count=self.count_spin.value(),
            interval_ms=self.interval_spin.value(),
        )
        self.poller.data_received.connect(self.on_data_received)
        self.poller.connection_state.connect(self.on_connection_state)
        self.poller.error.connect(self.on_error)
        self.poller.finished.connect(self.on_worker_finished)

        self.set_settings_enabled(False)
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.status_label.setText("Conectando...")
        self.status_dot.setStyleSheet("color: #d8a106; font-size: 18px;")
        self.poller.start()

    def stop_polling(self):
        if self.poller:
            self.poller.stop()
        self.disconnect_button.setEnabled(False)
        self.status_label.setText("Desconectando...")

    def on_connection_state(self, connected: bool, message: str):
        self.status_label.setText(message)
        if connected:
            self.status_dot.setStyleSheet("color: #1f9d55; font-size: 18px;")
        else:
            self.status_dot.setStyleSheet("color: #9e9e9e; font-size: 18px;")

    def on_worker_finished(self):
        self.set_settings_enabled(True)
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.poller = None

    def on_error(self, message: str):
        self.status_label.setText(message)
        self.status_dot.setStyleSheet("color: #c62828; font-size: 18px;")

    def on_data_received(self, timestamp: str, registers: list):
        self.last_registers = registers
        self.read_count += 1
        self.last_read_label.setText(f"Última leitura: {timestamp}")
        self.counter_label.setText(f"Leituras: {self.read_count}")

        self.table.setRowCount(len(registers))
        for offset, value in enumerate(registers):
            address = self.current_start_address + offset
            signed_value = as_signed_16(value)
            values = [
                str(address),
                str(value),
                f"0x{value:04X}",
                str(signed_value),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(offset, col, item)

        if self.logging_checkbox.isChecked() and self.poller:
            try:
                self.db.insert_reading_batch(
                    timestamp=timestamp,
                    port=self.poller.port,
                    slave_id=self.poller.slave_id,
                    function_code=self.poller.function_code,
                    start_address=self.current_start_address,
                    registers=registers,
                )
            except Exception as exc:
                self.status_label.setText(f"Leitura OK, erro ao salvar: {exc}")

        if self.graph_address is not None:
            index = self.graph_address - self.current_start_address
            if 0 <= index < len(registers):
                raw = registers[index]
                value = (
                    as_signed_16(raw)
                    if self.graph_mode_combo.currentData() == "signed"
                    else raw
                )
                self.graph_x.append(self.read_count)
                self.graph_y.append(value)

                if len(self.graph_x) > self.MAX_GRAPH_POINTS:
                    self.graph_x = self.graph_x[-self.MAX_GRAPH_POINTS :]
                    self.graph_y = self.graph_y[-self.MAX_GRAPH_POINTS :]

                self.curve.setData(self.graph_x, self.graph_y)

    def select_graph_register(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        self.graph_address = self.current_start_address + row
        self.graph_label.setText(f"Registrador {self.graph_address}")
        self.clear_graph()

    def rebuild_graph_value(self):
        self.clear_graph()

    def clear_graph(self):
        self.graph_x = []
        self.graph_y = []
        self.curve.setData([], [])

    def export_csv(self):
        default_name = (
            f"modbus_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar leituras",
            str(APP_DIR / default_name),
            "CSV (*.csv)",
        )
        if not file_name:
            return

        try:
            total = self.db.export_csv(Path(file_name))
            QMessageBox.information(
                self,
                "Exportação concluída",
                f"{total} registros exportados para:\n{file_name}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro na exportação",
                str(exc),
            )

    def closeEvent(self, event):
        if self.poller:
            self.poller.stop()
            self.poller.wait(2000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Monitor Modbus RTU")
    pg.setConfigOptions(antialias=True)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
