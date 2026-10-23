"""Transport boundary; no Qt, database or tag processing here."""
from typing import Protocol
import math
import time
from pymodbus.client import ModbusSerialClient, ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusIOException
from ..profiles import MEASUREMENT_MAP


class Transport(Protocol):
    def read(self, unit: int, function: int, address: int, count: int) -> list: ...
    def write(self, unit: int, function: int, address: int, values: list): ...
    def close(self): ...


class ModbusError(Exception): pass


def validate_range(function, address, count):
    if function not in (1,2,3,4) or not 1 <= count <= (2000 if function in (1,2) else 125) or not 0 <= address <= 65536-count:
        raise ValueError('Faixa Modbus inválida')


class ClientTransport:
    def __init__(self, device, trace=None):
        self.device = device
        self.trace = trace
        self.client = None

    def _packet(self, sending, data):
        if self.trace: self.trace('TX' if sending else 'RX', data.hex(' ').upper())
        return data

    def connect(self):
        if self.client is None:
            d = self.device
            args = dict(timeout=d.timeout, retries=d.retries, trace_packet=self._packet)
            self.client = (ModbusSerialClient(port=d.port, baudrate=d.baudrate, parity=d.parity, bytesize=d.bytesize, stopbits=d.stopbits, **args)
                           if d.transport == 'RTU' else ModbusTcpClient(d.host, port=d.tcp_port, **args))
        if not self.client.connected and not self.client.connect(): raise ConnectionError('Não foi possível conectar')

    @staticmethod
    def _check(result):
        if isinstance(result, ModbusIOException): raise TimeoutError(str(result))
        if result.isError(): raise ModbusError(str(result))
        return result

    def read(self, unit, function, address, count):
        validate_range(function,address,count)
        self.connect()
        method = {1:'read_coils',2:'read_discrete_inputs',3:'read_holding_registers',4:'read_input_registers'}[function]
        try: r = self._check(getattr(self.client,method)(address,count=count,device_id=unit))
        except ModbusIOException as e: raise TimeoutError(str(e)) from e
        except ConnectionException as e: raise ConnectionError(str(e)) from e
        data = r.bits if function in (1,2) else r.registers
        if len(data) < count: raise ModbusError('Resposta incompleta')
        return data[:count]

    def write(self, unit, function, address, values):
        if function not in (1,3): raise ValueError('Função não gravável')
        validate_range(function,address,len(values))
        if not self.client or not self.client.connected:
            raise ConnectionError("Escrita exige conexão já estabelecida; comando não enviado")
        # Disable automatic retries for writes: lost acknowledgement is ambiguous.
        old = self.client.transaction.retries
        self.client.transaction.retries = 0
        try:
            if function == 1:
                if len(values) != 1: raise ValueError('Somente uma coil por comando')
                result = self.client.write_coil(address,bool(values[0]),device_id=unit)
            elif len(values) == 1: result = self.client.write_register(address,values[0],device_id=unit)
            else: result = self.client.write_registers(address,values,device_id=unit)
            self._check(result)
        finally: self.client.transaction.retries = old

    def close(self):
        if self.client: self.client.close()


class Simulator:
    """Synthetic map ONLY. Never used to infer a real device's map."""
    def __init__(self, device, trace=None):
        self.mode = 'normal'
        self.values = {}
        self.device=device
        self.trace=trace

    def read(self, unit, function, address, count):
        validate_range(function,address,count)
        if self.mode == 'offline': raise ConnectionError('Simulação offline')
        if self.mode == 'timeout': raise TimeoutError('Timeout simulado')
        t = time.monotonic()
        if self.device.measurement_profile == MEASUREMENT_MAP:
            if function != 4 or address + count > 26:
                raise ModbusError('Mapa de demonstração: somente FC04, endereços 0–25')
            if self.trace: self.trace('SIM', f'Unit {unit} FC04 @{address} n={count}; valores sintéticos')
            volts = [int((250 if self.mode == 'alarme' else 220) * 100 + 250 * math.sin(t/3 + n)) for n in range(3)]
            amps = [int(500 + 35 * math.sin(t/4+n)) for n in range(3)] + [65]
            frequencies = [6000] * 7
            factors = [95, 96, 94]
            active = [int(volts[n]/100 * amps[n]/100 * factors[n]/100) for n in range(3)]
            apparent = [int(volts[n]/100 * amps[n]/100) for n in range(3)]
            reactive = [int(math.sqrt(max(0, apparent[n]**2-active[n]**2))) for n in range(3)]
            values = volts + amps + frequencies + factors + active + reactive + apparent
            return values[address:address+count]
        synthetic = [int(2200+30*math.sin(t/3)), int(470+25*math.sin(t/5)), int(1030+40*math.sin(t/4)), int((950 if self.mode=='alarme' else 650)+20*math.sin(t/6))]
        electrical=[]
        for phase in range(4):
            angle=t/3+phase+self.device.unit_id
            volts=(25+8*math.sin(angle)) if phase==3 else (2500 if self.mode=='alarme' else 2200)+30*math.sin(angle)+self.device.unit_id*5
            amps=(60+15*math.sin(angle)) if phase==3 else 400+self.device.unit_id*80+phase*20+25*math.sin(angle)
            electrical.extend([int(volts),int(amps)])
        if self.trace: self.trace('SIM',f'Leitura sintética Unit {unit} FC{function:02} @{address} n={count} (sem transporte físico)')
        return [self.values.get((function,a), bool(int(t/3)%2) if function in (1,2) else electrical[a-100] if 100<=a<108 else synthetic[a] if a < 4 else a % 65536) for a in range(address,address+count)]

    def write(self, unit, function, address, values):
        self.read(unit,function,address,len(values))
        for i,v in enumerate(values): self.values[(function,address+i)] = v

    def close(self): pass


def make_transport(device, trace=None):
    return Simulator(device,trace) if device.transport == 'SIM' else ClientTransport(device,trace)
