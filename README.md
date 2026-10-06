# Storobot – posts automáticos no LinkedIn para a Storopack

Automação 100% em **GitHub Actions + GitHub Pages**:

| Workflow | Quando | O que faz |
|---|---|---|
| `generate.yml` | todo dia 08:00 BRT, mas só age a cada **30 dias** | Lê storopack.com.br → Gemini cria plano de 12 temas → copy de cada post → imagem (ilustração IA + título + logo original) |
| `post.yml` | todo dia 10:00 BRT, mas só age a cada **3 dias** | Publica no perfil pessoal do LinkedIn o próximo post **aceito** |
| `set-status.yml` | disparado pelos botões da página | Muda o status do post; ao aceitar, chama o `post.yml` (publica na hora se já passaram 3 dias) |
| `subscribe.yml` | disparado pelo botão de notificações | Cadastra o aparelho para receber notificações push |
| `pages.yml` | após cada workflow acima | Publica a página de aprovação (`docs/`) |

Os dados ficam no próprio repositório: `docs/data/posts.json`, `docs/data/state.json` e `docs/images/`.

Status de um post: `generating → pending → accepted | rejected → posted` (ou `failed` se a geração falhar).

## Configuração (uma vez)

### 1. Repositório
1. Crie um repositório **público** no GitHub (Pages gratuito exige repo público; os segredos continuam protegidos, mas posts e imagens ficam visíveis) e faça push deste projeto na branch `main`.
2. **Settings → Pages → Source: GitHub Actions**.
3. **Settings → Actions → General → Workflow permissions: Read and write**.

### 2. Gemini
1. Gere uma chave em <https://aistudio.google.com/apikey>.
2. **Settings → Secrets and variables → Actions → New secret**: `GEMINI_API_KEY`.
3. Geração de imagem pode exigir billing ativo no projeto do Google AI Studio (12 imagens/mês, custo baixo).
4. Opcional (Variables): `GEMINI_TEXT_MODEL`, `GEMINI_IMAGE_MODEL` para trocar os modelos padrão (`gemini-3.8-flash` / `gemini-3.1-flash-image`).

### 3. LinkedIn (API oficial gratuita, perfil pessoal)
1. Em <https://www.linkedin.com/developers/apps> crie um app (exige associar a uma página de empresa — pode ser qualquer página que o vendedor administre ou uma página simples criada para isso; os posts saem no **perfil pessoal**).
2. Aba **Products**: adicione **Sign In with LinkedIn using OpenID Connect** e **Share on LinkedIn** (ambos self-service e gratuitos).
3. Aba **Auth**: em *Authorized redirect URLs* adicione `http://localhost:8765/callback`. Copie *Client ID* e *Client Secret* para o `.env` local (veja `.env.example`).
4. Na sua máquina, logado no LinkedIn do vendedor:
   ```bash
   pip install -r requirements.txt
   python scripts/linkedin_auth.py --set-secrets   # usa o gh CLI; sem a flag, só imprime os valores
   ```
   Isso grava os secrets `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` e a variable `LINKEDIN_TOKEN_CREATED_AT`.

> ⚠️ O token do "Share on LinkedIn" vale **60 dias** e não tem renovação automática (refresh token é só para parceiros do LinkedIn). Faltando 7 dias, o workflow abre uma **Issue** no repositório lembrando de rodar o passo 4 de novo.

### 4. Página de aprovação
1. Acesse `https://<usuario>.github.io/<repo>/`.
2. Crie um **fine-grained personal access token** (<https://github.com/settings/personal-access-tokens/new>) com acesso **apenas a este repositório** e permissão **Actions: Read and write**.
3. Na página, clique em **Acesso** e cole o token (fica salvo só naquele navegador).
4. Aceitar/Recusar dispara o `set-status.yml`; a página mostra "sincronizando" até a mudança ser publicada (~1–2 min).

### 5. App no celular (PWA) e notificações
- **Instalar**: no Android/Chrome, botão **Instalar** no topo do painel. No iPhone, Safari → Compartilhar → **Adicionar à Tela de Início** (o botão mostra as instruções).
- **Notificações**: botão do sino. Avisa quando chegam posts novos para aprovar e quando um post é publicado. No iPhone só funciona pelo app instalado (iOS 16.4+). Cada aparelho ativa uma vez.
- As notificações são enviadas pelos próprios workflows (Web Push). Exigem o secret `VAPID_PRIVATE_KEY`; a chave pública correspondente está em `docs/config.js`. As inscrições dos aparelhos ficam criptografadas em `data/push_subscriptions.enc`.
- Para gerar um novo par de chaves (só se precisar trocar; os aparelhos terão de ativar de novo):
  ```bash
  python -c "import base64;from py_vapid import Vapid02;from cryptography.hazmat.primitives import serialization as s;b=lambda x:base64.urlsafe_b64encode(x).rstrip(b'=').decode();v=Vapid02();v.generate_keys();print('privada',b(v.private_key.private_numbers().private_value.to_bytes(32,'big')));print('publica',b(v.public_key.public_bytes(s.Encoding.X962,s.PublicFormat.UncompressedPoint)))"
  ```

### 6. Primeira execução
**Actions → Gerar posts → Run workflow → mode: force**. Em seguida aprove os posts no painel: o primeiro aceito é publicado na hora (não há post anterior), e os seguintes a cada 3 dias.

## Uso no dia a dia
- Aprovar/recusar posts na página.
- `generate.yml` com `mode: retry-failed` refaz posts que falharam.
- `post.yml` com `force` publica o próximo aceito imediatamente.
- Se não houver nenhum aceito no dia de postar, ele publica assim que algum for aceito (o aceite dispara o `post.yml`).

## Rodar localmente
```bash
python -m venv .venv && .venv/Scripts/activate      # Windows (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env                                  # preencha as chaves
set PYTHONPATH=src                                    # Linux/Mac: export PYTHONPATH=src
python -m storobot.generate --force --limit 2         # gera 2 posts de teste
python scripts/serve.py                               # abre a página em http://localhost:8000 (sem cache)
python -m storobot.set_status 001-01 accepted
python -m storobot.post --dry-run                     # mostra o texto sem publicar
```

## Estrutura
```
src/storobot/       código Python (generate, post, set_status, notify, gemini, linkedin, image_compose, site_context)
scripts/            linkedin_auth.py (token), commit_push.sh (commit com retry), serve.py (página local)
docs/               painel/PWA (GitHub Pages) + dados + imagens
data/               inscrições de notificação (criptografadas)
assets/fonts/       Source Sans 3 (fonte do site da Storopack, licença OFL)
cache/              resumo do site usado como contexto pelo Gemini
```

## Observações
- O cron do GitHub pode atrasar alguns minutos; o intervalo de 3/30 dias é garantido pelas datas em `state.json`.
- O GitHub desativa crons após 60 dias sem atividade no repositório; os commits automáticos do bot evitam isso.
- Logo e título são desenhados por código (Pillow) sobre a ilustração da IA, garantindo o logo original e o texto sem erros.
