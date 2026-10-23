# Cobertura e pendências da primeira passagem

## Implementado

- RTU e TCP no mesmo contrato; múltiplos dispositivos; um dono por COM; configurações persistentes e campos condicionais.
- Tags configuráveis com os sete tipos solicitados, ordem de bytes/palavras, escala, offset, unidade, decimais, polling/histórico/atividade e limites de escrita.
- Monitoramento incremental com qualidade e bruto/HEX; dashboard com cards, estado booleano, texto editável, resumo dos dispositivos e gráfico; seleção de tags persistente.
- Múltiplas séries, zoom/pan, pausa, limpeza, janelas e buffers limitados.
- SQLite WAL, histórico por tag/tempo, presets/período, gráfico, CSV completo em fluxo e retenção configurável.
- Alarmes de comparação, booleanos e perda de comunicação, severidade, reconhecimento, normalização e persistência de ocorrências.
- Escrita de coil/register/múltiplos registers, confirmação, validação, auditoria, bloqueio por tag, sem retry/replay.
- Scanner limitado, cancelável e somente leitura; captura opcional RX/TX e operação/latência; diagnóstico de dispositivo.
- Logs rotativos; caminhos de dados apropriados para Windows/EXE; núcleo headless; simulação interna com falhas e servidor TCP local.
- Testes automatizados e scripts de execução/empacotamento.

## Antes de uso operacional contínuo

1. Validar no Windows com conversor e equipamento reais: driver, polaridade, mapas, ordens, tempos, desconexão/reconexão, fechamento durante timeout, escrita e resposta perdida. Nenhum hardware físico esteve disponível nesta sessão.
2. Gerar e validar dist/MonitorModbus.exe no Windows, inclusive execução sem Python instalado e permissões do usuário.
3. Medir carga com número real de dispositivos/tags e comparar latência/CPU/memória com ScadaBR. O objetivo de desempenho ainda não foi demonstrado por comparação.
4. Definir os limites operacionais e perfis de permissão necessários antes de uso de controle por vários operadores.

## Próximas evoluções, não implementadas agora

- Editor livre de dashboards, vários painéis, arrastar/redimensionar, gauges e eixos/unidades separados. O painel atual é fixo com seleção de tags e texto persistentes.
- Polling por tag; ajuste de frequências; métricas percentis/ciclos e benchmark prolongado.
- Histerese, temporização, debounce, deadband, latch, notificações e usuários de reconhecimento; alarme offline independente de uma tag. Hoje requer uma tag ativa com polling no dispositivo.
- Paginação completa de histórico de alarmes; interface para consulta de comandos; política de retenção de auditoria e alarmes. Hoje comandos estão no SQLite e logs; tela de alarmes limita a 2.000 eventos.
- Min/max/downsampling histórico e navegação além de 20.000 amostras em tela (CSV já exporta tudo).
- Importação em lote de tags/perfis e migração assistida do banco legado. Não interpretar registros antigos automaticamente.
- Retenção adaptativa para taxas acima da limpeza atual; fila durável/reenvio de histórico em falha de banco, backup automatizado e recuperação de interrupções abruptas.
- Scanner com configuração temporária independente do cadastro, descoberta de escravos e decodificador de frames. Atualmente usa um dispositivo cadastrado e operação independente com polling parado.
- UX em monitores pequenos, revisão de acessibilidade, atalhos e divisão de main_window.py em páginas menores. Regras de processo já estão fora dela.
- Camada formal de autorização, PostgreSQL, API/WebSocket, serviço Windows, acesso remoto e infraestrutura distribuída — somente em fases futuras.

## Comportamentos que devem ser conhecidos

- Pausa de gráfico não para aquisição. Limpar gráfico não apaga SQLite.
- Tag sem polling não gera alarmes, atualizações ou nova qualidade. Dispositivo sem tags em polling fica Sem leitura.
- Um erro em qualquer tag marca o dispositivo com erro ao fim do ciclo; qualidade de cada tag permanece individual.
- Regra desabilitada preserva ocorrência ativa até ser reabilitada e reavaliada; não se infere normalização sem evidência.
- IDs de configuração persistem ao editar, histórico não copia nomes/unidades a cada amostra. Se uma tag mudar de unidade/endereço, crie outra tag para não misturar séries com significados diferentes.
- Escritas não são comandos de segurança funcional ou intertravamentos. Modbus confirmou o protocolo, não o resultado físico.
