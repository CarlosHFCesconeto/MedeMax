import math
import struct
from .models import TYPES, Tag


def decode(registers, tag: Tag):
    tag.validate()
    if len(registers) != tag.count: raise ValueError('Resposta incompleta')
    if tag.data_type == 'Boolean': return bool(registers[0])
    words = [int(x).to_bytes(2, 'big') for x in registers]
    if tag.word_order == 'little': words.reverse()
    if tag.byte_order == 'little': words = [x[::-1] for x in words]
    raw = struct.unpack('>' + TYPES[tag.data_type][0], b''.join(words))[0]
    value = raw * tag.scale + tag.offset
    if not math.isfinite(value): raise ValueError('NaN/Inf recebido')
    return value


def encode(value, tag: Tag):
    tag.validate()
    if not tag.writable: raise ValueError('Tag somente leitura')
    value = float(value)
    if not math.isfinite(value) or not tag.write_min <= value <= tag.write_max: raise ValueError('Valor fora dos limites de escrita')
    if tag.data_type == 'Boolean':
        if value not in (0,1): raise ValueError('Tipo Lógico aceita apenas 0/1')
        return [bool(value)]
    raw = (value-tag.offset)/tag.scale
    if tag.data_type.startswith(('UINT','INT')):
        if not math.isclose(raw, round(raw), abs_tol=1e-7, rel_tol=0): raise ValueError('Valor não representável com a escala configurada')
        raw = round(raw)
    try: data = struct.pack('>' + TYPES[tag.data_type][0], raw)
    except (struct.error, OverflowError) as e: raise ValueError('Valor fora da faixa do tipo') from e
    words = [data[i:i+2] for i in range(0,len(data),2)]
    if tag.byte_order == 'little': words = [w[::-1] for w in words]
    if tag.word_order == 'little': words.reverse()
    return [int.from_bytes(w,'big') for w in words]
