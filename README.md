# MedeMax v0.3.6

O programa utiliza o Python e as bibliotecas compartilhadas do computador. **Abra `run.bat` para iniciar:** ele não cria ambiente virtual e não instala bibliotecas. Se alguma dependência estiver ausente, execute **`instalar_dependencias.bat`** uma vez. Novas pastas de atualização usam a mesma instalação de Python. O título, a tela Sobre e o log identificam a versão **0.3.6**.

As configurações, os dispositivos e o histórico continuam no mesmo diretório de dados do usuário. O `test.bat` e o `build_exe.bat` também usam o Python compartilhado; esses comandos de desenvolvimento instalam as dependências de testes/build quando executados.

# Modo de apresentação

No Dashbord, clique em **Apresentação • F11**, ou pressione **F11** em qualquer tela para abrir o Dashbord em tela cheia. Mantém o dispositivo/painel selecionado e as preferências de visualização. Oculta menu lateral, cabeçalho de aquisição, título redundante e rodapé técnico.

- Os cards e gráficos continuam atualizando; a aquisição/histórico/alarmes seguem funcionando.
- Na visão geral, os dispositivos selecionados também exibem seus valores atuais. No painel individual, as tensões ficam na primeira linha e as correntes na segunda.
- A barra compacta mantém **Dispositivos**, **Medições**, **Visão geral** e **Sair • Esc**.
- **Opções** mostra/oculta os filtros de organização, unidade e janela, pausa/eixos automáticos e controles locais de estilo dos gráficos.
- Pressione **Esc**, **F11** ou **Sair • Esc** para sair, restaurando a janela e a tela anterior. Sair da apresentação não para a aquisição.
- Com muitos gráficos/dispositivos, a rolagem permanece disponível. Não há paginação/ciclo automático de telas.

Cards trifásicos do painel individual: primeira linha Tensão 1 / 2 / 3 / N; segunda linha Corrente 1 / 2 / 3 / N. A apresentação reconhece nomes Tensão L1 ou Tensão 1 etc.; não altera nomes, IDs, endereços ou histórico das tags.

# Visualizações e seleção do Dashbord

- **Dispositivos** abre uma seleção com busca, selecionar todos e limpar. Aplicar salva os dispositivos visíveis. Ocultar não interrompe aquisição/histórico/alarmes; desativar a comunicação é feito no cadastro do dispositivo.
- **Medições** seleciona tags dos dispositivos visíveis, ou do dispositivo aberto. A seleção é salva e preserva as preferências dos demais dispositivos.
- **Organizar**: Por dispositivo; Todos no mesmo gráfico; Por unidade; Uma medição por gráfico. Funciona na visão geral e no painel individual. O modo é salvo.
- No cabeçalho de cada gráfico, escolha **Linhas, Degraus, Pontos ou Área**. A escolha é salva por grupo de gráfico. Área usa zero como base.
- A legenda abaixo dos gráficos identifica **dispositivo • medição [unidade]**. Desmarcar uma entrada oculta temporariamente a série naquele gráfico. Para salvar a seleção de tags, use Medições.
- Cores são estáveis por tag. Não indicam severidade de alarme.
- **Por unidade** é útil para visualizar tensões e correntes sem achatar a corrente no eixo das tensões. O filtro de unidades inclui as unidades cadastradas, não só V/A. Um gráfico conjunto usa um eixo Y compartilhado.
- Controles: janela até 24h, pausa, eixos automáticos e Ajustar eixos em cada gráfico. Desmarcar Eixos automáticos permite explorar com zoom; Ajustar eixos enquadra uma vez. Pausa congela gráficos; cards continuam atualizando.
- Os cards da visão geral abrem os painéis individuais. Duplo clique no gráfico Por dispositivo também abre o painel. Voltar retorna à seleção da visão geral.
- Monitoramento e Histórico também incluem o dispositivo no nome das séries.

# Dashbord por dispositivo e demonstração trifásica

1. Pare a aquisição e clique em **Simular 3 medidores**. São criados três dispositivos SIM, cada um com tensão/corrente L1, L2, L3 e N (24 tags). Repetir o botão não duplica os dispositivos. Cadastros existentes são preservados; se houver outros dispositivos, eles também aparecem no Dashbord.
2. Clique em **Iniciar aquisição**. O período inicial dos novos simuladores é 100 ms, editável em Dispositivos com a aquisição parada.
3. No Dashbord, escolha **Gráficos separados** ou **Gráfico conjunto**. A preferência de agrupamento é salva.
4. Clique em **Abrir painel**, ou dê duplo clique no gráfico separado, para ver apenas aquele dispositivo com seus cards. Use **Todos os dispositivos** para voltar.
5. Selecione V ou A para comparar uma unidade. Todas as unidades compartilham o eixo Y; grandezas de menor amplitude podem parecer achatadas. Os filtros/janela são independentes do Monitoramento. Há pausa, eixos automáticos e janelas até 24h.
6. Em Diagnóstico, ative **Capturar recebimentos/envios (RX/TX)** para ver operações SIM/OP sintéticas. Modos timeout/offline/alarme se aplicam a todos os simuladores em execução. Não são frames físicos nem teste de vazão RS485. O modo alarme produz sobretensão L1 nos novos medidores; retorno a normal normaliza as regras.

O mapa 100–107 é exclusivamente fictício. Tensão do neutro usa uma referência fictícia; não define o circuito real. A simulação percorre aquisição, conversão de tags, histórico e alarmes. Não reproduz latência de cabo, USB, RTU ou TCP. Leituras continuam por tag, sem agrupamento Modbus.

# MedeMax 0.3.6 — supervisório Modbus do Grupo Maxwell

Aplicativo desktop em **Python, PySide6, PyQtGraph, PyModbus e SQLite**. Interface em português; aquisição independente de Qt. RTU, TCP e simulação usam o mesmo fluxo de tags.

Esta entrega é uma primeira versão funcional de engenharia. Não representa homologação em equipamentos reais. O código original completo está em `legacy/`.

## Começar no Windows

Use Python **3.11 ou 3.12, 64 bits** no computador. Extraia o ZIP inteiro. O MedeMax usa o Python compartilhado encontrado pelo comando `python`. Se a TI já instalou as dependências nesse Python, basta abrir `run.bat`. Se faltarem bibliotecas, execute `instalar_dependencias.bat` uma vez e depois abra `run.bat`.

Ou, no PowerShell dentro da pasta:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Para instalar ou ajustar dependências após uma atualização, use `instalar_dependencias.bat` ou o comando `python -m pip install -r requirements.txt`. Instale e execute com o mesmo comando `python` e a mesma conta do Windows. A instalação pode precisar de internet; abrir o programa não executa pip. `run.bat`, `test.bat` e `build_exe.bat` não criam nem utilizam ambiente virtual. Uma `.venv` antiga pode ser removida com o programa fechado; ela não é necessária para esta versão.

### Sem hardware: demonstração imediata

```powershell
python main.py --demo
```

A opção `--demo` utiliza um banco separado em `simulation/`, cria quatro tags sintéticas e inicia a aquisição. Tensão, corrente, potência e temperatura variam com o tempo. Todos os endereços e escalas da demonstração são **fictícios**.

Também há o botão **Criar demonstração**: ele adiciona um dispositivo SIM ao banco atualmente aberto, sem substituir seus cadastros. Depois clique em Iniciar aquisição. Uma segunda execução desse botão não duplica a demonstração.

Em **Diagnóstico → Simulação**, selecione `timeout`, `offline` ou `alarme`. O alarme de temperatura sintética dispara acima de 80 °C. Volte a `normal` para recuperar a comunicação/normalizar. A reconexão usa espera progressiva; a recuperação pode levar até 30 segundos. Uma escrita em uma tag simulada fixa seu valor até reiniciar a aquisição.

### Servidor TCP real de desenvolvimento

Em outro terminal:

```powershell
python tools\simulate_tcp.py
```

Cadastre dispositivo TCP com `127.0.0.1`, porta `15020`, Unit ID `1`. O servidor está limitado ao computador local. Seu mapa fictício usa FC03/FC04, endereços 0..3 com valores iniciais 2203, 470, 1030 e 650; endereços 4..99 iniciam em zero. Os valores desse servidor são estáticos e graváveis; a variação e injeção de falhas estão no transporte SIM. As áreas do servidor são compartilhadas para simplificar o teste, não modelam um equipamento industrial específico.

## Dispositivos e RTU / RS485

1. Pare a aquisição antes de cadastrar ou editar.
2. Abra **Dispositivos → Adicionar**. Escolha Modbus RTU, Modbus TCP ou Simulação.
3. Para RTU, selecione/digite a COM exibida no Gerenciador de Dispositivos. Configure baud, paridade, data bits, stop bits, Slave ID, timeout, retries e intervalo **conforme o manual**. O programa detecta as portas ao abrir o formulário.
4. Para TCP, informe hostname/IP e porta (padrão 502), Unit ID e os tempos. Campos exclusivos da serial ficam ocultos.
5. Ative o dispositivo e cadastre as tags. Clique em **Iniciar aquisição**.
6. Observe qualidade, última leitura, média do tempo e contador de erros em Diagnóstico.

Múltiplos escravos na mesma COM compartilham um worker e um cliente serial; use iguais parâmetros seriais, timeout e retries em seus cadastros. Os Slave IDs podem ser diferentes. TCP utiliza um cliente por dispositivo. Os dispositivos não são iniciados automaticamente na abertura normal.

O cabeamento RS485, polaridade A/B, referência, terminação e parâmetros devem seguir os manuais do conversor/equipamento. Não há descoberta automática de baud ou Slave ID. Não abra a mesma COM em outro programa.

## Tags

**Tags → Adicionar**. Cadastre nome, descrição, dispositivo, função, endereço, tipo, ordens, escala, offset, unidade e decimais. Configure polling, histórico, atividade e permissão/limites de escrita.

- FC01: coils; FC02: discrete inputs; FC03: holding registers; FC04: input registers.
- Endereços são **base zero de protocolo**, 0..65535. Não copie automaticamente rótulos como 40001. Confirme a convenção do fabricante.
- Boolean: 1 bit (FC01/02) ou 1 register (FC03/04, zero=falso).
- UINT16/INT16: 1 register; UINT32/INT32/FLOAT32: 2; FLOAT64: 4.
- A quantidade é calculada pelo tipo. Para monitorar um bloco bruto, crie tags UINT16 por endereço ou use o scanner.
- Byte order `little` troca os bytes dentro de cada palavra; word order `little` inverte a sequência de palavras. `big/big` preserva a ordem recebida.
- `valor_real = valor_bruto × escala + offset`. Boolean exige escala 1 e offset 0.
- Slave/Unit ID pertence ao dispositivo. Para outro escravo na mesma COM, cadastre outro dispositivo. Tags não armazenam COM/IP.
- Não há mapas de dispositivos reais embutidos. Sem manual, use UINT16, escala 1, offset 0 e nomes neutros.

A Watch List mostra valor, unidade, qualidade, horário, dispositivo e registradores brutos em decimal/hex. Valores de falha aparecem como `—`; não se apresentam como uma leitura válida antiga. Qualidades: OK, Timeout, Offline, Erro Modbus e Sem leitura. Quando a aquisição para, a tela identifica os valores como Parado.

## Dashbord e gráficos

Marque as tags na lista do **Monitoramento**. A seleção persiste e alimenta os cards e as séries do Dashbord. Boolean é apresentado como Ativo/Inativo. O painel tem texto editável, estado dos dispositivos e gráfico de linhas.

Há legenda, zoom/pan nativos do PyQtGraph, pausa visual, limpeza e janelas de 1/5/15/60 minutos. Pausar não interrompe aquisição nem histórico. Cada tag mantém no máximo **3.600 pontos**, portanto o tempo disponível também depende do polling (500 ms ≈ 30 min). A atualização da interface ocorre a 5 Hz; curvas são reutilizadas e dados brutos não acumulam indefinidamente. Diferentes unidades compartilham o mesmo eixo nesta versão; selecione séries comparáveis.

## Histórico e CSV

Selecione uma ou várias tags, um período predefinido ou Personalizado e clique **Consultar**. Presets: 5 minutos, 1 hora, hoje, 24 horas, 7 dias. Datas da interface são locais; armazenamento usa timestamp UTC.

O gráfico retorna no máximo as **20.000 amostras mais recentes do filtro**; a tabela mostra as últimas 500. O CSV exporta **todo o período selecionado**, em fluxo, sem carregar tudo em memória. Usa UTF-8 com BOM, `;` e vírgula decimal para Excel pt-BR, timestamps ISO UTC, nome/ID da tag, ID do dispositivo, valor e qualidade. Consultas e exportação rodam em segundo plano.

Retenção padrão: **30 dias**, alterável em Configurações. Limpeza em lotes de até 10.000 amostras por minuto. Espaço liberado é reutilizado pelo SQLite; o arquivo não necessariamente encolhe. Alarmes e auditoria de comandos não são expurgados automaticamente.

## Alarmes

Em **Alarmes → Nova regra**, selecione a tag, condição (`>`, `<`, `==`, ativo, inativo, offline), limite, severidade e mensagem. `offline` considera Offline/Timeout do dispositivo, observado através da tag escolhida; essa tag precisa estar ativa e com polling habilitado.

Ativação, valor, reconhecimento e normalização persistem. Reconhecer não encerra o alarme. Normalizar não exclui o evento. Desmarque **Somente ativos** para consultar o histórico (últimos 2.000 eventos). Uma falha de qualidade não normaliza um alarme numérico, porque o valor é desconhecido. Eventos ativos são recuperados ao reiniciar; a condição é reavaliada na primeira leitura. Regra desabilitada não gera/normaliza eventos enquanto desabilitada. Não é permitido excluir uma regra que ainda tenha evento ativo.

## Controle / escrita

Configure **Permitir escrita** e os limites reais na tag (somente FC01 e FC03). Com aquisição ativa e leitura recente OK, selecione a linha em Monitoramento e clique **Escrever na tag selecionada**. Digite o valor já escalado; Boolean aceita 0/1. Confirme o resumo antes do envio.

A conversão inversa valida faixa, escala, valor finito e representabilidade inteira. Um register usa FC06; múltiplos usam FC16; coil usa FC05. Fila limitada, uma escrita pendente por tag, prazo de 3 segundos antes de envio, sem retries de escrita e sem replay após reinício/reconexão. Comando e resultado são auditados no banco (`commands`) e no log rotativo.

**Indeterminado** significa que o equipamento pode ter executado, mas a resposta não foi confirmada. Confira a leitura/estado físico antes de repetir. **Confirmado** significa resposta Modbus aceita, não garantia de que o processo físico atingiu o valor. Não há autenticação/perfis de usuário nesta versão; a futura autorização deve ficar no serviço de comandos, não apenas na tela.

## Scanner e RX/TX

Pare a aquisição. Em Diagnóstico, selecione um dispositivo cadastrado (ele fornece COM/baud ou host), FC01..04, início e fim. **Escanear** faz requisições de um endereço, com 50 ms entre operações, zero retries e limite de 512 endereços. Cancelar interrompe entre operações; uma chamada em andamento ainda espera seu timeout. Exibe resposta bruta, HEX/INT16 e erros. Não faz escritas nem conclui o significado dos endereços.

Ative **Capturar recebimentos/envios (RX/TX)** durante aquisição para visualizar bytes reportados pelo `trace_packet` do PyModbus. As entradas OP mostram dispositivo, Unit, função, endereço, quantidade, tempo e resultado. Em serial os bytes incluem o frame RTU; TCP inclui MBAP. Dependendo de fragmentação, callbacks podem conter buffers parciais/acumulados, não necessariamente um frame por linha. O modo SIM registra apenas operações, não inventa tráfego físico. Captura limitada a 1.000 entradas e desativada por padrão.

## Dados, logs e backup

Windows: `%LOCALAPPDATA%\MonitorModbus\monitor.db`; logs em `logs\monitor.log`. Linux: `~/.local/share/MonitorModbus`. `--demo` usa subpasta `simulation`. Para diretório alternativo, use `--data-dir CAMINHO`. Diretórios são criados automaticamente fora da pasta temporária do EXE.

Um bloqueio de processo impede duas instâncias de usar o mesmo diretório de dados. Feche o programa e copie a pasta para backup. Configuração e histórico são persistidos automaticamente. Logs rotativos: 2 MB × 6 arquivos (atual + 5). Problemas de persistência aparecem no rodapé; a fila de histórico é limitada a 20.000 amostras e perdas são contadas. **Não é um historiador sem perda em falhas de disco/queda de energia**.

O banco legado `data/modbus_monitor.db` não é migrado automaticamente: tinha registradores sem identidade de tag. Preserve-o e use a exportação do programa anterior quando necessário. Nenhum banco antigo foi fornecido ou alterado nesta entrega.

## Núcleo sem interface

```powershell
python main.py --headless --demo --seconds 10
```

Sem `--seconds`, permanece ativo até Ctrl+C. `--headless` sem `--demo` usa a configuração normal. Comunicação, aquisição, histórico e alarmes funcionam sem QApplication. Não foi criado servidor web.

## Testes e EXE

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python main.py --demo --smoke-test
```

`test.bat` facilita a execução dos testes. Teste RTU por PTY é exclusivo de POSIX e é pulado no Windows; TCP local, conversões, persistência, alarmes e UI não exigem equipamento.

Execute **`build_exe.bat` no Windows**. Resultado esperado: **`dist\MonitorModbus.exe`**. PyInstaller precisa gerar o executável no sistema alvo. O EXE Windows não foi produzido/testado nesta sessão Linux. Dependências foram fixadas nas versões efetivamente usadas nos testes.

## Arquivos principais

- `app/main.py`: bootstrap, diretórios, log, modo desktop/headless.
- `app/models.py`, `app/codec.py`: domínio, validação e conversão.
- `app/communication/transports.py`: contrato, RTU/TCP e SIM.
- `app/services/core.py`: serviço de aplicação, polling, fila de comandos, scanner e escrita do histórico.
- `app/services/alarms.py`: ciclo de vida dos alarmes.
- `app/storage.py`: repositório SQLite.
- `app/ui/main_window.py`, `app/ui/forms.py`: telas e formulários.
- `tools/simulate_tcp.py`: servidor Modbus local de desenvolvimento.
- `tests/`: testes automatizados sem hardware físico.
- `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, `docs/ROADMAP.md`: decisões, validação e pendências.

Leia as pendências antes de usar para supervisão contínua de equipamentos reais. Não foi medido desempenho comparativo contra o ScadaBR.

## Identidade MedeMax e seção Sobre

A navegação **Sobre** apresenta o projeto MedeMax, o Grupo Maxwell, os oito integrantes e seus contatos. Os e-mails são links que abrem o aplicativo de e-mail; nenhum e-mail é enviado automaticamente. As duas imagens fornecidas foram incluídas sem alterações em `assets/medemax.png` e `assets/grupo_maxwell.png`.

Para adicionar o logo da UniSATC, coloque a imagem com o nome exato **`logosatc.png`** em **`assets/`** e reabra o aplicativo. No EXE, também é possível colocar `logosatc.png` ao lado de `MonitorModbus.exe`, sem recompilar. Se o arquivo não estiver presente, a seção mantém o nome da instituição, sem imagem quebrada ou logo inventado. O script de build inclui a pasta assets.

A marca visível agora é MedeMax; o caminho de dados `%LOCALAPPDATA%\MonitorModbus` e o nome do executável `MonitorModbus.exe` foram mantidos para compatibilidade. Seus cadastros e histórico existentes continuam no mesmo lugar.
