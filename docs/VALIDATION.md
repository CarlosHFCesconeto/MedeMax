# Validação da entrega 0.3.0

25/09/2026. Ambiente Linux, Python 3.12, PySide6 6.11.2, PyQtGraph 0.13.7, PyModbus 3.13.1 e pyserial 3.5.

## Resultado executado

`python -m pytest -q`: **47 passed in 4.70s**.

- Vetores conhecidos UINT16/INT16/UINT32/INT32/FLOAT32/FLOAT64 nas quatro combinações byte/word order, encode/decode, Boolean, escala/offset, limites, NaN/Inf, representabilidade e validações.
- Persistência após reabertura, filtro temporal por tag, CSV, valores ausentes e retenção.
- Condições numéricas/booleanas/offline, ativação sem duplicação, reconhecimento idempotente, normalização e recuperação após reinício do motor de alarmes.
- Aquisição headless simulada, escrita e leitura subsequente, alarme, perda/recuperação de comunicação e recusa de escrita offline.
- Parâmetros incompatíveis na mesma COM rejeitados; scanner limitado/cancelável.
- Processo servidor Modbus TCP local: FC01/02/03/04/05/06/16, exceção de protocolo e captura TX/RX.
- RTU por pseudo-terminal POSIX: leitura FC03, escrita FC06 e frames com CRC. Não simula eletrônica, ruído ou conversor USB.
- Servidor TCP recebe escrita e não confirma: exatamente um envio apesar de retries de leitura configurados em 3. Escrita recusa conexão ausente.
- UI Qt offscreen: abertura, campos condicionais RTU/TCP, escala decimal com vírgula, Watch List, séries e fechamento.
- Bloqueio entre processos usando o mesmo diretório de dados.

## Verificações adicionais

- `python main.py --headless --demo --seconds 2 --data-dir ...`: execução/encerramento normais e histórico gravado, sem QApplication.
- `QT_QPA_PLATFORM=offscreen python main.py --demo --smoke-test --data-dir ...`: janela criada, aquisição iniciada e encerramento normal, retorno 0. Avisos propagateSizeHints são do backend offscreen.
- Dashboard capturado e inspecionado visualmente: navegação, cards, estados e gráfico sem sobreposição. Imagem ilustrativa em dashboard.png.
- Os cinco arquivos originais foram lidos integralmente e preservados em legacy/.

## Não verificado

Nenhum equipamento/conversor RS485 físico disponível. Não houve execução nativa Windows, compilação/execução do EXE, comparação de desempenho com ScadaBR ou ensaio prolongado sob carga industrial. Testes locais não constituem homologação de controle de processo.

Próximo ensaio: no Windows, executar demonstração, depois um endereço bruto conhecido do equipamento; validar tipo/escala pelo manual; ampliar gradualmente; testar desconexão/reconexão; somente então habilitar escrita em bancada com limites definidos.

## Atualização 0.3.1 — MedeMax / Sobre

Identidade MedeMax aplicada ao cabeçalho, título da janela e ícone. Seção Sobre com logos originais, apresentação, oito integrantes/contatos e vínculo institucional. Assets adicionados ao comando PyInstaller.

Verificações desta atualização: compilação de sintaxe; comparação SHA-256 comprovando cópias idênticas das duas imagens; abertura/fechamento Qt offscreen; oito integrantes; ícone carregado; logo institucional ausente sem imagem quebrada; resolução e exibição de logo externo opcional em ambiente EXE simulado; captura da tela Sobre revisada visualmente (`sobre.png`). Os 47 testes acima são os resultados registrados da versão 0.3.0, não uma nova execução nesta atualização visual. Build nativo Windows continua pendente.


Atualização 01/10/2026: 50 testes passaram em ambiente Linux/offscreen, incluindo janela de 24h com pico e memória limitada, consulta acima de 20 mil amostras abrangendo o período, intervalo de 20ms e eixos automáticos. Não é benchmark de um mês real nem teste Windows/hardware físico.

Dashboard por dispositivo: 51 testes passaram; 3 dispositivos/24 tags, idempotência da criação, modo conjunto/separado, drill-down, filtro de unidade e aquisição integrada. Tela renderizada e conferida em Linux/offscreen.

Revisão de design: 52 testes passaram, incluindo seleção persistente de dispositivos, modos por unidade/medição, quatro estilos com dados, legendas com dispositivo e continuidade da aquisição de dispositivos ocultos. Conferidas telas geral e individual renderizadas.

Modo apresentação: 53 testes passaram. Validada entrada/saída por botão e teclado, ocultação/restauração dos menus, opções, navegação por dispositivo, 24 valores na visão geral e continuidade da aquisição. Tela de apresentação renderizada e conferida em Linux/offscreen; validação visual Windows permanece pendente.


## Atualização 23/10/2026 — mapa de 26 variáveis

65 testes passaram em Linux/Python 3.12/Qt offscreen. Incluem mapa FC04 0–25 com escalas da tabela; formatos UINT16/INT16; aplicação por dispositivo idempotente e recusa integral de conflitos; 26 tags decodificadas e persistidas a partir de uma requisição; modo individual com 26 requisições; falhas de bloco; limites do protocolo e lacunas; três medidores na mesma COM com Slave IDs diferentes e tag sem polling; demonstrações antigas preservadas; prévia do mapa e cartões.

Integração TCP real local: mapa conhecido gravado no simulador e lido em uma operação FC04 com 26 registradores. RTU em pseudo-terminal: requisição FC04 início 0/quantidade 26 e resposta com CRC. Não representa validação de eletrônica RS485/USB física.

Interface do diálogo e painel individual capturados e inspecionados. As dependências de produção permanecem as mesmas. Não foi gerado nem testado EXE Windows. Firmware real, sinal dos campos, larguras e índice base zero ainda precisam de confirmação na bancada. A hora comum do bloco é hora de recepção, não timestamp do ESP.


## Atualização 23/10/2026 — exclusão em conjunto

71 testes passaram em Linux/Qt offscreen. Os seis novos casos cobrem exclusão de 26 tags e suas regras; preservação de outro medidor, medições e eventos; encerramento administrativo de alarme ativo sem alterar sua normalização; persistência após reabertura; rollback após falha intermediária no banco; recusa de confirmação desatualizada; dispositivo vazio e bloqueio durante aquisição; botões Cancelar/Excluir e quantidades no aviso; atualização das tabelas/painel. Aviso de exclusão capturado e conferido visualmente.

A tabela adicional retired_alarm_rules é criada automaticamente nos bancos existentes para distinguir eventos encerrados por exclusão. Não se apagam amostras ou eventos nessa operação. Traduções foram inventariadas por inspeção do código, dos botões Qt e dos menus reais dos gráficos; aplicação geral depende do OK do usuário. Não houve teste nativo Windows nesta revisão.


## Atualização 23/10/2026 — tradução aprovada

73 testes passaram em Linux/Python 3.12/Qt offscreen (10,90 s). Os dois novos testes verificam Salvar/Cancelar/Aplicar/Sim/Não e menus de texto, calendário pt_BR, edição sem alterar os valores de dispositivo/tag/regra, modos de simulação com códigos preservados, estados traduzidos sem mudar a qualidade armazenada, nomes Dashbord/Tags, menus dos gráficos nas três telas e exportação CSV com separador e organização de colunas traduzidos e valores numéricos preservados. Os 71 testes anteriores também passaram, incluindo exclusão em conjunto e comunicação RTU/TCP local. Há seis avisos de depreciação na criação de parâmetros de exportação pelo pyqtgraph 0.13.7.

Foram renderizados e inspecionados visualmente a visão geral, cadastro de dispositivo, menu de eixos e diálogo de exportação. Este foi ampliado para os textos em português. O catálogo qtbase_pt_BR.qm acompanha assets e o build já coleta essa pasta. Não houve geração/execução de EXE nem ensaio nativo Windows nesta atualização.


## v0.3.6 — Python compartilhado (23/10/2026)

`run.bat` usa `python main.py`, sem criar ambiente virtual ou executar pip. `instalar_dependencias.bat` instala manualmente requirements.txt no mesmo Python. Testes e build também usam o comando python compartilhado. Nenhuma pasta de ambiente virtual do usuário é removida automaticamente. O título da janela, Sobre e log foram atualizados para 0.3.6; documentação acompanha o novo fluxo.

Verificação dos quatro scripts confirmou ausência de criação/uso de venv e ausência de instalação na abertura normal. A interface foi criada, exibida e encerrada em Qt offscreen/Linux; título e Sobre conferidos como 0.3.6. Nenhuma alteração na aquisição ou no banco. Os 73 testes registrados na revisão anterior não foram repetidos para esta mudança de iniciadores/rótulos. Scripts .bat foram salvos com CRLF; execução real desses scripts e build Windows permanecem pendentes.
