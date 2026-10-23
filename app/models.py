"""Domain configuration. Addresses are always zero-based protocol addresses."""
from dataclasses import dataclass, field
from uuid import uuid4
import math


def uid():
    return uuid4().hex


TYPES = {'Boolean': ('?', 1), 'UINT16': ('H', 1), 'INT16': ('h', 1),
         'UINT32': ('I', 2), 'INT32': ('i', 2), 'FLOAT32': ('f', 2), 'FLOAT64': ('d', 4)}


@dataclass
class Device:
    name: str = 'Novo dispositivo'
    description: str = ''
    transport: str = 'RTU'
    port: str = 'COM5'
    baudrate: int = 9600
    parity: str = 'N'
    bytesize: int = 8
    stopbits: float = 1
    host: str = '127.0.0.1'
    tcp_port: int = 502
    unit_id: int = 1
    timeout: float = 1
    retries: int = 1
    interval_ms: int = 1000
    enabled: bool = True
    read_blocks: bool = False
    measurement_profile: str = ''
    id: str = field(default_factory=uid)

    def validate(self):
        if not self.name.strip() or self.transport not in ('RTU', 'TCP', 'SIM'): raise ValueError('Nome/conexão inválidos')
        if not 1 <= self.unit_id <= (247 if self.transport == 'RTU' else 255): raise ValueError('Identificador Modbus inválido; envio para todos os endereços bloqueado')
        if not .05 <= self.timeout <= 10 or not 0 <= self.retries <= 3: raise ValueError('Tempo limite: 0,05–10 s; novas tentativas: 0–3')
        if not 20 <= self.interval_ms <= 3600000: raise ValueError('Intervalo de consulta: 20–3600000 ms')
        if self.transport == 'RTU' and (not self.port.strip() or self.baudrate <= 0 or self.parity not in ('N','E','O') or self.bytesize not in (7,8) or self.stopbits not in (1,1.5,2)): raise ValueError('Parâmetros seriais inválidos')
        if self.transport == 'TCP' and (not self.host.strip() or not 1 <= self.tcp_port <= 65535): raise ValueError('Endereço IP ou nome de rede/porta TCP inválidos')

    def bus_key(self):
        # One owner for each physical serial bus, independently of slave ID.
        return ('RTU', self.port.strip().upper()) if self.transport == 'RTU' else (self.transport, self.id)


@dataclass
class Tag:
    name: str = 'Nova tag'
    device_id: str = ''
    description: str = ''
    function: int = 3
    address: int = 0
    count: int = 1
    data_type: str = 'UINT16'
    byte_order: str = 'big'
    word_order: str = 'big'
    scale: float = 1
    offset: float = 0
    unit: str = ''
    decimals: int = 2
    writable: bool = False
    polling: bool = True
    history: bool = True
    enabled: bool = True
    write_min: float = -1e12
    write_max: float = 1e12
    id: str = field(default_factory=uid)

    def validate(self):
        if not self.name.strip() or not self.device_id: raise ValueError('Nome e dispositivo obrigatórios')
        if self.data_type not in TYPES or self.function not in (1,2,3,4): raise ValueError('Tipo/função inválido')
        if self.count != TYPES[self.data_type][1]: raise ValueError('Quantidade deve corresponder ao tipo (1, 2 ou 4)')
        if self.function in (1,2) and self.data_type != 'Boolean': raise ValueError('Saídas/entradas digitais exigem tipo Lógico (0/1)')
        if not 0 <= self.address <= 65536-self.count: raise ValueError('Endereço fora de 0–65535')
        if self.byte_order not in ('big','little') or self.word_order not in ('big','little'): raise ValueError('Ordem inválida')
        if not all(math.isfinite(x) for x in (self.scale,self.offset,self.write_min,self.write_max)): raise ValueError('Valores devem ser finitos')
        if self.write_min > self.write_max or not 0 <= self.decimals <= 9: raise ValueError('Limites/decimais inválidos')
        if self.writable and (self.function not in (1,3) or self.scale == 0): raise ValueError('Escrita exige função 01/03 e escala diferente de zero')
        if self.data_type == 'Boolean' and (self.scale != 1 or self.offset != 0): raise ValueError('Tipo Lógico (0/1) exige escala 1 e ajuste adicional 0')


@dataclass
class AlarmRule:
    name: str = 'Novo alarme'
    tag_id: str = ''
    condition: str = '>'
    threshold: float = 0
    severity: str = 'Aviso'
    message: str = ''
    enabled: bool = True
    id: str = field(default_factory=uid)

    def validate(self):
        if not self.name.strip() or not self.tag_id: raise ValueError('Nome e tag obrigatórios')
        if self.condition not in ('>','<','==','ativo','inativo','offline'): raise ValueError('Condição inválida')
        if self.severity not in ('Informação','Aviso','Alta','Crítica') or not math.isfinite(self.threshold): raise ValueError('Severidade/limite inválido')


@dataclass(frozen=True)
class Sample:
    timestamp: float
    tag_id: str
    device_id: str
    value: float | bool | None
    quality: str
    raw: tuple = ()
    detail: str = ''
