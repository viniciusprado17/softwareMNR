# Roteiro da demonstração com o protótipo real (fase nacional, 23 a 29/11)

Base: Seção 14 da especificação, adaptada à montagem real (Uno + 2 Heltec) que funcionou ponta a
ponta em 19/11/2026. Diferenças a declarar: `docs/ARTIGO_X_DEMONSTRACAO.md` e `docs/PROTOTIPO_UNO.md`.

## 1. Montar e abrir (5 minutos antes)

1. Antenas LoRa rosqueadas nas duas Heltec. Antena do GPS com a face branca para cima.
2. **Receptora** no cabo marcado **DADOS**, no notebook.
3. **Transmissora** e **Uno** no notebook (terra em comum pela USB e pelo fio GND direto).
   Powerbank só se for testado antes: ele desliga sozinho com consumo baixo.
4. Duplo clique no atalho **iniciar_demo.bat** (Área de Trabalho). Ele acha a receptora sozinho e
   abre a tela. Se não achar, oferece o modo simulado (Plano B).
5. Na tela: **Restaurar demo**. Esperar 2 ou 3 pacotes chegarem.
6. Conferência rápida (opcional, outro PowerShell): `python tools/teste_ponta_a_ponta.py`.
   Ele termina com **Restaurar demo**, a tela fica limpa.

## 2. Os 5 minutos no estande

1. **Problema (30 s):** vacinas e órgãos precisam ficar entre 2 e 8 °C; um registro de temperatura
   pode ser adulterado no caminho. A ideia: assinar a leitura na origem.
2. **Hardware (60 s):** SHT31 no Arduino Uno, a Heltec transmissora assina cada leitura com
   ECDSA P-256 (88 ms no ESP32) e manda por LoRa 915 MHz. A receptora entrega ao notebook.
   Mostrar o OLED das duas placas. **Gelo** no sensor: a temperatura cai para a faixa segura (OK);
   tirar do gelo ou segurar com a mão: sobe até ALERTA e ALARME.
3. **Gateway (45 s):** na tela, cada pacote aceito, com RSSI e SNR reais, entrando na corrente.
4. **Ataque 1, adulteração (45 s):** "Adulterar pacote" muda a temperatura de um pacote real:
   `ASSINATURA INVÁLIDA`, o pacote falso não entra.
5. **Ataque 2, replay (30 s):** "Reenviar pacote": assinatura válida, mas `REPLAY` (seq já usado).
6. **Corrente (60 s):** "Verificar corrente" (verde). "Adulterar o banco" (alguém apaga um alarme
   direto no SQLite). "Verificar corrente" de novo: vermelho, com o hash gravado e o recalculado.
7. **Resultados e limites (30 s):** tabela de `docs/MEDICOES.md` e os limites abaixo.
8. **Restaurar demo** antes do próximo grupo.

## 3. O que dizer com franqueza

- O artigo validou em simulação Python; aqui o mesmo fluxo roda em hardware real.
- Curva P-256 no protótipo (artigo: secp256k1), ambas de 256 bits; escolha por ser padrão de IoT.
- Assinatura medida no ESP32: 88 ms. Não comparar com os 0,59 ms do artigo (PC, Python).
- A assinatura é feita na Heltec; o fio do Uno até a Heltec leva texto sem autenticação.
  Em produção o sensor fica no próprio nó, com a chave num elemento seguro.
- LoRa ponto a ponto, não LoRaWAN. Sem GSM e sem nuvem. Demonstração toda local, sem internet.
- GPS: recebe sentenças válidas; posição só com céu aberto (dentro do estande, "sem fix").
- Não é blockchain: é uma corrente de hash, sem consenso distribuído.

## 4. Se algo falhar na hora

| Sintoma | O que fazer |
|---|---|
| Tela parada, OLED da receptora recebendo | Porta errada: fechar a tela e rodar `python tools\achar_portas.py` |
| OLED da transmissora "SENSOR: ERRO" | Terra: transmissora e Uno no notebook; conferir fio GND direto |
| Tudo em REPLAY | Clicar em Restaurar demo |
| Nada funciona | `iniciar_demo.bat` e responder S (modo simulado), declarando à banca |

## 5. Levar na viagem

- 2 Heltec com antenas, Arduino Uno com cabo USB-B, SHT31, GPS com antena, protoboard montada.
- Cabo USB-C de **dados** marcado e **um reserva de dados** (hoje só um funciona).
- Cabo USB-C de carga, powerbank, jumpers macho-fêmea e macho-macho reserva.
- Notebook com o projeto atualizado (`git pull`) e o atalho `iniciar_demo.bat` na Área de Trabalho.
- Recipiente pequeno para gelo (o sensor não é à prova d'água: gelo em saco plástico).
- Cópia do manual e do guia da equipe (`prototipo_lacor/`).
