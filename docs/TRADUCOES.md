# Revisão de idioma — traduções aplicadas (23/10/2026)

Traduções aprovadas e aplicadas. O usuário optou por **Dashbord** no título e na navegação e por manter **Tags**. Os nomes de dispositivos e tags, identificadores internos, dados persistidos e códigos Modbus são preservados.

## Botões e janelas comuns

Locais: adicionar/editar dispositivo, tag e regra; seleção de dispositivos/medições no painel; confirmações de escrita e exclusão individual; exportação; menus dos campos de texto.

| Texto atual | Proposta |
|---|---|
| Save | Salvar |
| Cancel | Cancelar |
| Apply | Aplicar |
| Yes / No | Sim / Não |
| Close | Fechar |
| Open | Abrir |
| Undo / Redo | Desfazer / Refazer |
| Cut / Copy / Paste | Recortar / Copiar / Colar |
| Delete | Excluir |
| Select All | Selecionar tudo |
| File name / Files of type / Look in | Nome do arquivo / Tipo de arquivo / Examinar em |
| Configurar Device | Configurar dispositivo |
| Configurar Tag | Configurar medição (tag) |
| Configurar AlarmRule | Configurar regra de alarme |

OK permanece OK. Meses, dias da semana e calendários usam português brasileiro. A aplicação carrega o catálogo pt_BR do Qt incluído em assets e usa seus diálogos, incluindo seleção de arquivos, para que o idioma não dependa do Windows.

## Dispositivos

| Texto atual | Proposta |
|---|---|
| Baud rate | Taxa de transmissão (baud) |
| Data bits | Bits de dados |
| Stop bits | Bits de parada |
| Host / IP | Endereço IP ou nome de rede |
| Slave / Unit ID | Identificador Modbus (Slave / Unit ID) |
| Timeout (s) | Tempo limite de resposta (s) |
| Retries de leitura | Novas tentativas de leitura |
| Polling (ms) | Intervalo de consulta (ms) |

## Tags e regras de alarme

| Texto atual | Proposta |
|---|---|
| Byte order | Ordem dos bytes |
| Word order | Ordem dos registradores |
| big | Mais significativo primeiro (big-endian) |
| little | Menos significativo primeiro (little-endian) |
| Offset | Ajuste adicional (offset) |
| Polling habilitado | Consulta habilitada |
| Coils | Saídas digitais (Coils) |
| Discrete inputs | Entradas digitais |
| Holding registers | Registradores de retenção |
| Input registers | Registradores de entrada |
| Boolean | Lógico (0/1) |
| offline (condição de alarme) | Sem comunicação |

Tipos técnicos continuam identificados: UINT16, INT16, UINT32, INT32, FLOAT32 e FLOAT64, com descrições em português nos seletores. Números das funções Modbus permanecem iguais. Os códigos internos e os dados persistidos não devem mudar com o idioma.

## Monitoramento, painel e diagnóstico

| Texto atual | Proposta |
|---|---|
| Online | Conectado |
| Offline / offline | Sem comunicação |
| Timeout / timeout | Tempo de resposta excedido |
| True / False nas tabelas de configuração | Sim / Não |
| Boolean na instrução de escrita | Lógico (0 ou 1) |
| Scanner | Busca de registradores |
| Capturar RX/TX | Capturar recebimentos/envios (RX/TX) |
| HEX em cabeçalhos | Hexadecimal (HEX) |

O texto explicativo do mapa de 26 variáveis também usa "identificador Modbus" e "intervalo de consulta". Logs e exceções técnicas externas podem conservar o detalhe original para diagnóstico.

## Menus dos gráficos — painel, monitoramento e histórico

Inclui menu do botão direito, opções avançadas e dicas de ajuda.

| Texto atual | Proposta |
|---|---|
| ViewBox options | Opções de visualização |
| View All | Enquadrar todos os dados |
| X axis / Y axis | Eixo X / Eixo Y |
| Mouse Mode | Modo do mouse |
| 3 button / 1 button | 3 botões / 1 botão |
| Auto | Automático |
| Auto Pan Only | Apenas deslocamento automático |
| Visible Data Only | Somente dados visíveis |
| Invert Axis | Inverter eixo |
| Link Axis | Vincular eixo |
| Mouse Enabled | Interação com o mouse |
| None | Nenhum |
| Transforms | Transformações |
| Power Spectrum (FFT) | Espectro de potência (FFT) |
| Log X / Log Y | Escala logarítmica X / Escala logarítmica Y |
| Downsample | Redução de pontos |
| Subsample | Subamostragem |
| Mean | Média |
| Peak | Picos |
| Clip to View | Limitar à área visível |
| Average | Média de curvas |
| Forget hidden traces | Desconsiderar curvas ocultas |
| Max Traces | Máximo de curvas |
| Alpha | Transparência |
| Opacity | Opacidade |
| Grid | Grade |
| Show X Grid / Show Y Grid | Mostrar grade X / Mostrar grade Y |
| Points | Pontos |

Manual, dy/dx e fórmulas matemáticas permanecem como estão. A tradução do menu FFT não acrescenta análise de harmônicas da rede elétrica: ele continua operando sobre os dados desenhados.

## Exportação dos gráficos

| Texto atual | Proposta |
|---|---|
| Export / Export... | Exportar / Exportar... |
| Copy / Close | Copiar / Fechar |
| Export format / Export options | Formato de exportação / Opções de exportação |
| Item to export | Item a exportar |
| Image File (PNG, TIF, JPG, ...) | Arquivo de imagem (PNG, TIF, JPG, ...) |
| Scalable Vector Graphics (SVG) | Imagem vetorial (SVG) |
| CSV of original plot data | CSV dos dados originais do gráfico |
| HDF5 of plot data | HDF5 dos dados do gráfico |
| Matplotlib Window | Janela do Matplotlib |
| Printer / Print Document | Impressora / Imprimir documento |
| width / height / background | Largura / Altura / Fundo |
| antialias | Suavização de bordas |
| invertValue | Inverter luminosidade |
| scaling stroke | Ajustar espessura dos traços à escala |

Alguns formatos dependem de componentes opcionais. A revisão se aplica aos que forem exibidos, sem instalar novas ferramentas para oferecê-los.

## Nomes de telas — escolha aprovada

- Dashboard → **Dashbord** (grafia solicitada pelo usuário).
- **Tags** permanece **Tags**.

Modbus, RTU, TCP, IP, COM, CSV, FFT, códigos numéricos, nomes das bibliotecas e unidades V/A/W/var/VA/Hz são preservados. Nomes de dispositivos e medições definidos pelo usuário não são traduzidos automaticamente.

Histórico, Configurações, Sobre e modo de apresentação já estão majoritariamente em português; são abrangidos pelos ajustes dos diálogos, calendários e menus de gráficos aplicáveis.

Os seletores de exportação incluem Separador, Vírgula, Tabulação, Precisão e Organização das colunas. A árvore de itens usa Toda a área do gráfico, Gráfico e Área de visualização. A janela de exportação foi ampliada para acomodar os textos em português.
