# Atualização 23/10/2026

`profiles.py` define o mapa Input Registers 0–25 fornecido pela equipe e o planejador de leituras contíguas. `Core.apply_measurement_map` valida colisões antes de gravar dispositivo e novas tags em transação única. Dispositivos antigos mantêm leitura individual; aplicar o perfil habilita blocos por opção explícita. Uma requisição usa um horário de recepção comum, seguido da decodificação individual de cada tag. A aquisição física interna não é sincronizada pelo software. O SIM deste mapa é separado das demonstrações legadas.

# Arquitetura e análise da base original

## Análise antes da alteração

Foram lidos integralmente os cinco arquivos do ZIP original: main.py, README.md, requirements.txt, run.bat e build_exe.bat. A cópia integral está em legacy/.

Pontos preservados: Python/PySide6/PyQtGraph/PyModbus/SQLite, seleção de baud e porta, FC03/04, exibição UINT16/INT16/HEX, gráfico limitado, aquisição fora da thread principal e CSV com delimitador amigável ao Excel.

Limitações encontradas: main.py de aproximadamente 650 linhas concentrava UI/transporte/banco; um único intervalo de um escravo serial; configurações voláteis; conversão apenas de 16 bits; SQLite abria conexão por lote e era gravado no slot da UI; exportação usava fetchall; todas as células eram reconstruídas a cada resposta; faltavam retenção, alarmes, reconexão, logs e tags; fechamento esperava apenas 2 s e podia destruir QThread ainda em execução; dados ao lado do código seriam inadequados para EXE onefile.

A separação necessária justificou reconstruir o fluxo em módulos mantendo a implementação anterior intacta em legacy/. Não existe mapa de equipamento real assumido na nova base.

## Limites e responsabilidades

Device descreve um transporte e endereço de unidade. Tag contém interpretação e identidade de sinal, referenciando apenas device_id. AlarmRule referencia tag_id. Sample carrega timestamp UTC, valor, qualidade, bruto e diagnóstico. Os modelos não importam Qt nem clientes Modbus.

Transport define read(unit,function,address,count), write(unit,function,address,values) e close(). ClientTransport seleciona os clientes serial/TCP. Simulator implementa o mesmo contrato. Funções 01/02/03/04 são mapeadas dentro do transporte. O codec processa palavra/byte order, tipos, escala e offset independentemente do transporte.

Core oferece cadastro, aquisição, snapshots, consulta dos buffers e comandos. Não importa Qt. Um BusWorker por COM física serializa os escravos desse barramento. Um worker por dispositivo TCP permite progresso independente de outra conexão. Não há threads concorrendo sobre um cliente PyModbus.

As telas consomem snapshots a 200 ms; operações de rede estão nos workers. Séries usam deque(maxlen=3600). Uma fila limitada alimenta a thread historian, com inserções de até 500 amostras por transação. Alarmes são avaliados em cada Sample; eventos persistem separadamente das amostras. SQLite usa WAL, conexão persistente protegida por lock, índices por tag/tempo e por tempo. CSV usa conexão independente e cursor em fluxo. Consultas/exports/scanner usam executor da UI. Configuração e pequenos comandos de cadastro/reconhecimento são síncronos.

Há um snapshot em memória, não um barramento de eventos distribuído. Uma futura API poderá usar Core/snapshot/Repository e controlar o mesmo ciclo de vida. Não deve criar clientes Modbus paralelos ou contornar Core.write. HTTP, WebSocket, autenticação e cloud foram deliberadamente adiados conforme o escopo.

## Contratos de segurança de escrita

Antes da fila: validate + encode, dispositivo/tag ativos, leitura recente OK, auditoria de intenção e bloqueio de escrita pendente por tag. Na execução: aquisição ativa, comando ainda dentro do prazo, qualidade válida e nenhuma falha de comunicação pendente. A confirmação visual pertence à UI; limites/validação pertencem ao núcleo.

O transporte exige conexão existente e desativa retries durante a escrita, restaurando depois. Acesso à propriedade transaction.retries está isolado no adaptador e coberto por teste de resposta perdida; PyModbus está fixado em 3.13.1. Uma atualização da biblioteca precisa reexecutar testes de integração. Não existe replay de fila persistida. Auditoria abandonada em Enviando/Pendente após queda do processo deve ser investigada; não deve ser reenviada automaticamente.

## Estado e persistência

SQLite schema user_version=1. config guarda documentos JSON tipados e settings; samples armazena medidas indexadas; alarms contém um registro por ocorrência e ciclo de vida; commands mantém auditoria. IDs de domínio são UUIDs estáveis. Histórico permanece quando uma configuração é removida. Exclusões de dispositivo/tag com dependentes são bloqueadas. Não há importação automática do esquema legado.

Repository isola o SQL. Substituir por PostgreSQL exigirá outro adaptador com a mesma superfície de métodos e migrações; não basta trocar a string de conexão. Antes de alterações futuras de esquema, criar migrações versionadas explícitas.

## Performance e limites conhecidos

Aquisição é por tag, sem agrupamento automático de intervalos; isso evita ler lacunas ilegais sem mapa. O polling é um atraso após terminar o ciclo do dispositivo, não garantia de frequência exata. A taxa efetiva depende de baud, número de tags e timeouts. Backoff exponencial limitado a 30 s protege contra ciclos rápidos de falha. Threads por conexão são apropriadas à escala inicial; centenas de conexões exigirão benchmark e possivelmente scheduler assíncrono.

Não há promessa quantitativa de superar o ScadaBR sem medir ambos com o mesmo mapa/hardware. Buffer, fila, paginação e retenção foram limitados. A limpeza de 10.000 amostras/minuto pode exigir ajuste em altas taxas; observabilidade e benchmark estão no roadmap.

Referência técnica usada em conjunto com inspeção/teste da versão instalada: https://pymodbus.readthedocs.io/en/v3.13.0/source/client.html (API de cliente e trace_packet). A implementação usa device_id da versão 3.13.1, e não exemplos antigos baseados em slave.


## Idioma da interface

`app/ui/language.py` instala uma única vez o locale pt_BR, o catálogo Qt `assets/qtbase_pt_BR.qm` e um QTranslator específico para textos do pyqtgraph 0.13.7. Textos sem tradução retornam None para permitir a tradução Qt seguinte. Apenas títulos/legendas da interface mudam; nomes personalizados e valores de protocolo não passam por tradução. Os seletores salvam `currentData`, preservando tipos, funções, paridade, byte/word order e modos de simulação.

`localize_plot` ajusta os títulos dos eixos e encaminha a exportação para `PortugueseExportDialog`, que traduz títulos/limites de seleção sem mudar chaves e valores dos parâmetros. Os campos de faixa de eixos continuam com locale C porque o pyqtgraph os interpreta com float(). O nome interno de página Dashboard é preservado; seu título visível é Dashbord. Diálogos Qt são usados em todos os sistemas para manter o idioma.
