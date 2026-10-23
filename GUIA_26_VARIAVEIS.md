# MedeMax v0.3.6 — mapa de 26 variáveis (23/10/2026)

## Começar a medir

1. Feche a versão anterior, extraia este ZIP em outra pasta e abra `run.bat`.
   O programa usa o Python compartilhado do computador. Se faltarem bibliotecas, execute `instalar_dependencias.bat` uma vez. O histórico/configurações existentes continuam no diretório de dados do usuário.
2. Pare a aquisição. Em **Dispositivos**, adicione ou edite cada medidor com COM/baud/paridade/Slave ID (RTU) ou host/porta/Unit ID (TCP).
3. Selecione a linha do medidor e clique em **Aplicar mapa 26 variáveis**.
4. Confira os formatos e a prévia. Clique em **Aplicar mapa**. Repita para os outros medidores.
5. Clique em **Iniciar aquisição**. Confira valores e qualidade no Monitoramento e selecione os dispositivos/medições desejados no Dashbord.

Para testar sem placa, com a aquisição parada, use **Dispositivos → Simular mapa 26 variáveis** e depois **Iniciar aquisição**.
O dispositivo criado está claramente marcado SIM e seus valores são sintéticos. As demonstrações antigas continuam disponíveis e não usam esse mapa.

## Contrato usado

O mapa abaixo foi transcrito da tabela fornecida pela equipe. Assume **endereços de protocolo base zero e um inteiro de 16 bits por variável**.
Confirme isso no firmware antes de interpretar leituras reais. A tabela não informou representação com/sem sinal.

- Todos os pontos são **Input Registers, FC04**, somente leitura, com polling e histórico habilitados.
- Nos endereços 0–16, o medidor envia o valor multiplicado por 100: escala do programa **0,01**, offset 0. Exemplo: 22035 → 220,35 V; 6000 → 60,00 Hz; 95 → 0,95.
- Nas potências 17–25: escala **1**, offset 0.
- Padrão inicial: **UINT16**, sem sinal. No diálogo, potência ativa/reativa e fator de potência podem usar **INT16** se o firmware enviar inteiros com sinal em complemento de dois. Potência aparente permanece UINT16.
- Este perfil não atende diretamente FLOAT32, inteiros de 32 bits, sinal codificado em outro registrador ou mapa de endereços diferente. Nesse caso, ajuste o cadastro das tags conforme a documentação do firmware.
- I4 é apresentado como **Corrente 4**. Não foi presumido que seja neutro. Não há tensão do neutro no mapa. Os nomes podem ser editados em Tags.
- O mapa não inclui harmônicas, THD, energia acumulada ou forma de onda.

| Endereço | Medição | Unidade | Escala |
|---|---|---|---|
| 0 | Tensão 1 (RMS V1) | V | 0,01 |
| 1 | Tensão 2 (RMS V2) | V | 0,01 |
| 2 | Tensão 3 (RMS V3) | V | 0,01 |
| 3 | Corrente 1 (RMS I1) | A | 0,01 |
| 4 | Corrente 2 (RMS I2) | A | 0,01 |
| 5 | Corrente 3 (RMS I3) | A | 0,01 |
| 6 | Corrente 4 (RMS I4) | A | 0,01 |
| 7 | Frequência V1 | Hz | 0,01 |
| 8 | Frequência V2 | Hz | 0,01 |
| 9 | Frequência V3 | Hz | 0,01 |
| 10 | Frequência I1 | Hz | 0,01 |
| 11 | Frequência I2 | Hz | 0,01 |
| 12 | Frequência I3 | Hz | 0,01 |
| 13 | Frequência I4 | Hz | 0,01 |
| 14 | Fator de potência CH1 | adimensional | 0,01 |
| 15 | Fator de potência CH2 | adimensional | 0,01 |
| 16 | Fator de potência CH3 | adimensional | 0,01 |
| 17 | Potência ativa CH1 | W | 1 |
| 18 | Potência ativa CH2 | W | 1 |
| 19 | Potência ativa CH3 | W | 1 |
| 20 | Potência reativa CH1 | var | 1 |
| 21 | Potência reativa CH2 | var | 1 |
| 22 | Potência reativa CH3 | var | 1 |
| 23 | Potência aparente CH1 | VA | 1 |
| 24 | Potência aparente CH2 | VA | 1 |
| 25 | Potência aparente CH3 | VA | 1 |

## Requisições e preservação de dados

Com **Ler os 26 registradores em uma requisição por ciclo** marcado, o medidor recebe FC04, início 0, quantidade 26.
Uma resposta alimenta separadamente as 26 tags, gráficos, histórico e alarmes. As tags da mesma resposta recebem o mesmo horário de recepção no computador; isso não comprova simultaneidade da aquisição interna na placa.

A opção também fica disponível em **Editar dispositivo → Leitura em blocos contíguos**. É desativada por padrão nos dispositivos antigos.
Somente tags ativas com polling são incluídas; buracos no mapa e funções distintas geram requisições separadas. O limite por bloco é 125 registradores ou 2000 bits.
Se o equipamento recusar leitura em bloco, desmarque a opção para requisitar cada tag individualmente. Falhas em um bloco marcam suas tags com erro; valores antigos não são publicados como válidos.

Reaplicar o mesmo mapa não duplica tags. Se houver uma tag FC04 incompatível na faixa 0–25, a aplicação é recusada integralmente e informa o endereço; revise manualmente ou cadastre outro dispositivo.
Não há exclusão automática de tags antigas ou alteração de seus históricos. Tags de demonstração não são convertidas em medições reais.

Para vários medidores na mesma COM, configure parâmetros seriais iguais e um Slave ID distinto para cada placa. O programa mantém um worker compartilhado por barramento.
Não abra simultaneamente esse barramento com outro mestre Modbus. Para TCP, configure o IP/Unit ID efetivo de cada medidor/gateway. O IP 192.168.10.111 não foi aplicado automaticamente.

O polling continua ajustável em Dispositivos. A leitura em bloco reduz o número de requisições; a taxa obtida depende do baud rate, quantidade de medidores e firmware.
O programa não inicia aquisição real automaticamente. Validação física em Windows/RS485 continua necessária.
