# micro-ecc (copia local)

Copia sem alteracoes de https://github.com/kmackay/micro-ecc, commit
`541b3a78026420a3e369c4c9281c396b5e531113` (licenca BSD-2, ver `LICENSE.txt`).

Por que copia local: o ESP-IDF (Arduino-ESP32) ja embute no `libbt` uma copia do tinycrypt
com os MESMOS nomes publicos (`uECC_sign`, `uECC_verify`, ...), o que causa "multiple
definition" no linker. `../cc_uecc_rename.h` renomeia todos os simbolos para `cc_uECC_*` e
`../cc_uecc.c` compila esta copia com esses nomes. Nao compile `uECC.c` diretamente
(excluido em `library.json`).
