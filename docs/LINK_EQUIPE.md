# Link fixo para a equipe (modo simulado no Render)

A tela em **modo simulado** pode ficar online com um link fixo, sem depender do PC de ninguém. O modo com as placas continua local, porque o receptor LoRa fica no USB do computador.

O repositório já tem tudo configurado em `render.yaml`. Só falta conectar a conta.

## Passo a passo (uma vez só, cerca de 5 minutos)

1. Entre em **https://render.com** e clique em **Get Started**. Escolha **GitHub** para criar a conta.
2. No painel, clique em **New +** e depois em **Blueprint**.
3. Autorize o Render a ver o repositório **viniciusprado17/softwareMNR**. Se a lista estiver vazia, clique em **Configure account** e libere esse repositório.
4. Selecione o repositório. O Render lê o `render.yaml` e mostra o serviço **cadeia-de-frio-mnr** (plano Free).
5. Ele pede o valor de **CC_PASSWORD**. Digite a senha que a equipe vai usar para abrir a tela.
6. Clique em **Apply**. A primeira publicação leva de 2 a 4 minutos.
7. O link aparece no topo do serviço, no formato `https://cadeia-de-frio-mnr.onrender.com`. Se esse nome já existir, o Render acrescenta letras no final.

## Como a equipe acessa

- Abrir o link. O navegador pede **usuário e senha**: o usuário pode ser qualquer um (por exemplo `equipe`) e a senha é o `CC_PASSWORD`.
- Para trocar a senha: no Render, abrir o serviço, ir em **Environment**, editar `CC_PASSWORD` e salvar. Ele publica de novo sozinho.
- Sem senha (link aberto): apagar a variável `CC_PASSWORD`. Não recomendado, porque qualquer pessoa poderia usar os botões de ataque.

## O que saber do plano gratuito

- O site **dorme após 15 minutos sem acesso**. O primeiro acesso depois disso demora cerca de 30 a 60 segundos para acordar.
- Ao acordar ou a cada nova publicação, a demonstração **começa do zero** (os dados ficam só na memória). Isso é esperado.
- **Todos veem a mesma tela**: se alguém clicar em "Restaurar demo", zera para todos.
- A cada merge na `main`, o Render publica a versão nova automaticamente.

## Alternativa sem conta: link temporário do seu PC

Com o sistema rodando no Windows (`run_gateway.bat`), abra outro `cmd`:

```
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000
```

Ele mostra um link `https://....trycloudflare.com`. Funciona só enquanto o PC estiver ligado, e muda a cada execução. Para pôr senha também nesse caso: `run_gateway.bat --simulate --demo-controls --password SUA_SENHA`.
