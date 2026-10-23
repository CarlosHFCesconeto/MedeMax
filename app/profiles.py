"""Explicit register map supplied by the project team (one 16-bit word per value)."""
from .models import Tag

MEASUREMENT_MAP = 'medemax-input26-v1'
MAP_DESCRIPTION = 'Mapa MedeMax 26: FC04, endereços 0–25, um inteiro de 16 bits por variável.'


def measurement_tags(device_id, power_type='UINT16', factor_type='UINT16'):
    if power_type not in ('UINT16', 'INT16') or factor_type not in ('UINT16', 'INT16'):
        raise ValueError('Este mapa exige UINT16 ou INT16; confirme o formato no firmware')
    rows = []
    rows += [(f'Tensão {n}', 'V') for n in range(1, 4)]
    rows += [(f'Corrente {n}', 'A') for n in range(1, 5)]
    rows += [(f'Frequência V{n}', 'Hz') for n in range(1, 4)]
    rows += [(f'Frequência I{n}', 'Hz') for n in range(1, 5)]
    rows += [(f'Fator de potência CH{n}', '') for n in range(1, 4)]
    for quantity, unit in [('Potência ativa', 'W'), ('Potência reativa', 'var'), ('Potência aparente', 'VA')]:
        rows += [(f'{quantity} CH{n}', unit) for n in range(1, 4)]
    return [Tag(name=name, device_id=device_id, function=4, address=address,
                description=MAP_DESCRIPTION,
                data_type=factor_type if 14 <= address <= 16 else power_type if 17 <= address <= 22 else 'UINT16',
                scale=.01 if address <= 16 else 1, unit=unit,
                decimals=2 if address <= 16 else 0, writable=False)
            for address, (name, unit) in enumerate(rows)]


def read_plan(tags, grouped=False):
    """Group only adjacent/overlapping addresses of the same function, within protocol limits."""
    tags = list(tags)
    if not grouped:
        return [(t.function, t.address, t.count, [t]) for t in tags]
    result = []
    for tag in sorted(tags, key=lambda t: (t.function, t.address)):
        limit = 2000 if tag.function in (1, 2) else 125
        end = tag.address + tag.count
        if result:
            function, start, count, members = result[-1]
            if function == tag.function and tag.address <= start + count and end - start <= limit:
                result[-1] = (function, start, max(start + count, end) - start, members + [tag])
                continue
        result.append((tag.function, tag.address, tag.count, [tag]))
    return result
