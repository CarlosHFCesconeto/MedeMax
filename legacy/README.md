# Monitor Modbus RTU

Programa desktop para Windows que:

- detecta portas COM;
- conecta em Modbus RTU via serial/RS485;
- usa 9600 baud por padrão;
- lê Holding Registers (função 03) ou Input Registers (função 04);
- mostra os valores como UINT16, HEX e INT16;
- plota um registrador em tempo real;
- salva as leituras automaticamente em SQLite;
- exporta o histórico para CSV.

## 1. Requisitos

- Windows 10/11;
- Python 3.11, 3.12 ou 3.13;
- conversor USB ↔ RS485 instalado e aparecendo como porta COM.

## 2. Instalação

Abra o PowerShell nesta pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Ou dê duplo clique em `run.bat`. Na primeira execução ele cria o ambiente virtual e instala as dependências.

## 3. Configuração inicial

Os valores padrão são:

- Baud rate: selecionável (`300` a `115200` entre valores comuns), com `9600` como padrão
- Paridade: `N`
- Stop bits: `1`
- Data bits: `8`
- Slave ID: `1`
- Função: `03 - Holding Registers`
- Endereço inicial: `0`
- Quantidade: `10`
- Intervalo: `1000 ms`

A configuração exata depende do equipamento.

## 4. Endereços Modbus

O programa usa endereçamento base zero, como o PyModbus.

Isso é importante porque alguns manuais mostram endereços como `40001`, `40002`, etc., mas esses números não devem ser digitados diretamente sem verificar a convenção do fabricante.

Exemplo comum:

- manual `40001` -> endereço `0`
- manual `40002` -> endereço `1`

Mas confirme sempre no manual do equipamento.

## 5. Banco de dados

As leituras ficam em:

```text
data/modbus_monitor.db
```

Cada registrador lido gera uma linha com:

- data/hora;
- porta;
- Slave ID;
- função;
- endereço;
- valor UINT16;
- valor INT16.

## 6. Gráfico

Clique em qualquer linha da tabela de registradores. O programa passa a acompanhar aquele endereço no gráfico.

Você pode visualizar o mesmo registrador como:

- `UINT16`
- `INT16`

Quando tivermos o mapa de registradores do equipamento, a próxima versão pode transformar dois registradores em `FLOAT32`, aplicar escala, dar nomes como "Tensão", "Corrente", "Potência" etc. e criar vários gráficos específicos.

## 7. Gerar .exe

Execute:

```powershell
build_exe.bat
```

O executável será criado em:

```text
dist\MonitorModbusRTU.exe
```

## 8. Ligações RS485

Em geral:

```text
Conversor USB/RS485 A(+)  -> A(+) do equipamento
Conversor USB/RS485 B(-)  -> B(-) do equipamento
GND, quando necessário    -> GND de referência
```

Se não houver comunicação mesmo com a configuração correta, uma das primeiras verificações é inverter A/B, porque a nomenclatura varia entre fabricantes.

## Próxima etapa

Para transformar os registradores em grandezas reais, precisamos do mapa do equipamento, por exemplo:

| Endereço | Nome | Tipo | Escala |
|---|---|---|---|
| 0 | Tensão | UINT16 | 0,1 V |
| 1 | Corrente | UINT16 | 0,01 A |
| 2-3 | Potência | FLOAT32 | 1 W |

A estrutura do programa já está pronta para receber essa camada.
