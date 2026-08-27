# URANO Publication Bridge — Chrome Extension

Extensão Manifest V3 para usar a aba autenticada do próprio usuário como superfície de leitura, sem exportar a sessão do navegador.

## Modelo de segurança

- O usuário abre a página normalmente e faz login no site pelo Chrome.
- A extensão usa `activeTab`: só recebe acesso à aba quando o usuário clica no ícone.
- O script lê apenas o DOM renderizado da aba ativa: URL, título, DOI, metadados bibliográficos, seleção e texto principal.
- Cookies, senhas, localStorage do site, bearer tokens, refresh tokens e dados do perfil Chrome não são coletados.
- O conteúdo capturado é enviado somente ao bridge local em `127.0.0.1:8765`/`localhost:8765`.
- O backend mantém no máximo 20 capturas em memória e não persiste conteúdo em disco.

Isso permite aproveitar acesso institucional ou contas já autenticadas sem transformar o URANO em um gerenciador de credenciais ou mecanismo de bypass.

## Instalação local

1. Rode o bridge:

```bash
python3 -m src.urano_kernel.bridge
```

2. Abra `chrome://extensions`.
3. Ative **Modo do desenvolvedor**.
4. Clique em **Carregar sem compactação** e selecione a pasta `chrome-extension/`.
5. Fixe `URANO Publication Bridge` na barra do Chrome.

## Uso

1. Abra uma publicação ou serviço no qual você já esteja autenticado.
2. Se desejar analisar só um trecho, selecione-o.
3. Clique no ícone da extensão.
4. `OK` indica que a captura foi entregue ao bridge local; `ERR` indica que o bridge está offline ou rejeitou a captura.

Quando um DOI é detectado, o bridge também executa o `publication_resolver` e devolve os handoffs para análise científica.

## Endpoints locais

```text
POST /api/browser/capture
GET  /api/browser/captures
GET  /api/browser/capture/<capture_id>
```

A extensão não contorna CAPTCHA, paywall ou autenticação. Ela apenas lê uma página que o próprio usuário já conseguiu abrir legitimamente na sua sessão atual.
