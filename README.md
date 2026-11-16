# Robô de ofertas e vitrine Papai Achou

O robô busca ofertas na Shopee 6 vezes por dia (7h, 10h, 13h, 16h, 19h e 22h). Ele filtra pelos critérios do canal, confere o histórico de preço e manda as 5 melhores para o seu Telegram privado, cada uma com foto, comissão e o texto pronto para o canal. Você escolhe as que valem, posta no canal do Telegram e encaminha para o Canal do WhatsApp.

Ele roda de graça no GitHub, mesmo com o computador desligado.

## O que você precisa antes

1. Conta na **Shopee Afiliados** aprovada e acesso à **Open API** (no painel de afiliado, seção Open API). Ali você copia o **App ID** e o **Secret**.
2. Conta no **Telegram** (no chip do canal).
3. Conta no **GitHub**.

## Passo 1 — Criar o robô no Telegram (5 minutos)

1. No Telegram, procure **@BotFather** (o perfil oficial, com selo azul) e mande `/newbot`.
2. Nome do robô: `Papai Achou Ofertas`. Usuário: algo como `papaiachou_ofertas_bot` (precisa terminar em `bot`).
3. O BotFather responde com um **token** (algo como `123456:ABC-xyz...`). Guarde: é a senha do robô, não mostre a ninguém.
4. Abra o seu robô novo e mande `/start`. É isso que permite que ele fale com você.

## Passo 2 — Subir o código no GitHub

1. No GitHub, clique em **New repository**, dê o nome `papai-achou` e marque **Public**. O site gratuito do GitHub Pages só funciona em repositório público no plano grátis. Isso é seguro: as chaves ficam guardadas nos segredos (passo 3), nunca no código.
2. Na página do repositório vazio, clique em **uploading an existing file** e arraste todo o conteúdo desta pasta, incluindo a pasta `.github`.
   - A pasta `.github` começa com ponto e pode ficar oculta no computador. No Windows, ative "Itens ocultos" no Explorador. No Mac, aperte `Cmd + Shift + .` no Finder.
3. Clique em **Commit changes**.

## Passo 3 — Guardar as chaves (segredos)

No repositório: **Settings › Secrets and variables › Actions › New repository secret**. Crie estes 4 segredos:

| Nome | Valor |
|---|---|
| `SHOPEE_APP_ID` | App ID da Open API da Shopee |
| `SHOPEE_SECRET` | Secret da Open API da Shopee |
| `TELEGRAM_TOKEN` | Token que o BotFather deu |
| `TELEGRAM_CHAT_ID` | Seu chat_id (veja abaixo) |

**Como descobrir o seu chat_id:** com o `/start` já mandado ao robô, abra no navegador
`https://api.telegram.org/bot<SEU_TOKEN>/getUpdates` (troque `<SEU_TOKEN>` pelo token, sem os sinais `< >`).
Procure `"chat":{"id":` e copie o número que vem depois. Esse é o seu chat_id.

## Passo 4 — Primeiro teste

No repositório: aba **Actions › Robô Papai Achou › Run workflow**. Em 1 ou 2 minutos as ofertas chegam no seu Telegram. A partir daí ele roda sozinho nos horários.

Se der erro, abra a rodada na aba Actions, clique no passo vermelho e me mande o texto do erro.

## Passo 5 — Colocar a vitrine no ar

A vitrine é o site que fica na pasta `docs`. O robô atualiza o arquivo `docs/ofertas.json` a cada rodada, e o site mostra as ofertas sozinho.

1. No repositório: **Settings › Pages**.
2. Em **Build and deployment**, escolha **Deploy from a branch**, branch `main` e pasta `/docs`. Clique em **Save**.
3. Em 1 ou 2 minutos aparece o endereço do site, algo como `https://SEU-USUARIO.github.io/papai-achou/`. Com o domínio próprio, o endereço oficial é `https://opapaiachou.com.br` — esse é o link para as bios.
4. Abra `docs/config.js` (ícone de lápis) e troque os `"#"` pelos links do Canal do WhatsApp, do Telegram, do Instagram e do TikTok.

**Ofertas do Mercado Livre e da Amazon (manuais):** abra `docs/manuais.csv` e acrescente uma linha por oferta, neste formato:

```
data,categoria,loja,nome,preco,preco_antigo,link,foto
2026-11-20,Presentes,Mercado Livre,"Kit Churrasco Inox 10 Peças",89.90,149.90,https://link-de-afiliado,https://link-da-foto
```

- `categoria`: Fitness, Casa e cozinha, Escola, Crianças, Moda, Maquiagem e beleza, Tecnologia útil ou Presentes.
- `loja`: Mercado Livre ou Amazon.
- Preço com ponto, sem R$. Nome entre aspas se tiver vírgula. A foto é opcional.

**Domínio próprio (opcional):** depois de registrar `papaiachou.com.br` no Registro.br, coloque o domínio em **Settings › Pages › Custom domain** e siga as instruções de DNS que o GitHub mostra.

## Ajustes

Tudo fica em `robo/config.py`: as palavras pesquisadas e a categoria de cada uma na vitrine, a nota mínima, o desconto mínimo, a comissão mínima, a faixa de preço e quantas ofertas por rodada. Dá para editar direto no site do GitHub (ícone de lápis).

## Como o robô decide

- **Passa no filtro:** nota ≥ 4,5, pelo menos 100 vendas, desconto ≥ 20%, comissão ≥ 5% e preço entre R$ 10 e R$ 600.
- **Desconto real:** ele guarda o preço de cada produto a cada rodada (`dados/historico.json`). Se o produto já esteve mais barato antes, a "oferta" de agora é descartada.
- **Sem repetição:** o mesmo produto não volta antes de 7 dias.
- **Ordem:** o desconto pesa mais, depois a nota, as vendas, a comissão e se a loja é oficial.

Nos primeiros dias ainda não há histórico. Essas ofertas chegam marcadas com 🆕 para você conferir o preço antes de postar.

## Testar no computador (opcional)

```
pip install -r requirements.txt
python -m robo.main --demo
```

Mostra na tela os posts gerados a partir de produtos de exemplo, sem precisar de chaves.

## Limites, por regra das plataformas

- **WhatsApp:** a API oficial não publica em Canais, e ferramentas não oficiais arriscam banir o número. Por isso o encaminhamento é manual.
- **Mercado Livre:** não há API para gerar link de afiliado. O link sai do painel ou da extensão oficial.
- **Amazon:** a API exige 10 vendas qualificadas nos últimos 30 dias. Entra numa próxima versão.
