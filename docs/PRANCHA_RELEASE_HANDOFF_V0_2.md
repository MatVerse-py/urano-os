# Handoff da Prancha — GitHub / Product Hunt / AppDeploy

**Status:** DEMO_ONLY / STATIC_PREPARED / DEPLOY_HOLD (25/10/2026)

## Artefato para distribuição
- `index.html` independente com seis áudios MP3 e imagens embutidas.
- Identificação da build estática: SHA-256 `9bae870fefb63c079a5afa632e1a64d5d0b0d6c2a25c61f8f31efb68fc67ba1e`.
- Arquivo HTML: 4.668.964 bytes.
- Validação reproduzida nesta revisão: hash/tamanho, `node --check` do JavaScript inline, estrutura HTML parseada, seis PNG/seis MP3 com base64 e cabeçalhos válidos, IDs únicos e coerência dos claims/módulos exportados. [Relatório estático](prancha-demo-static-audit.json).
- **Não validado:** experiência real em navegador, responsividade e acessibilidade com aparelhos físicos.
- **Não versionado neste repositório:** mídia/HTML compilado; o arquivo fica no pacote local entregue ao usuário, para não inserir blob base64 de ~4,7 MB nesta especificação de runtime.

## Product Hunt — referências avaliadas
- Vizzu: animação quantitativa, https://www.producthunt.com/products/vizzu
- marimo: notebooks Python/SQL reativos e reprodutíveis, https://www.producthunt.com/products/marimo
- Faces: apresentações web exploráveis, https://www.producthunt.com/products/faces-4

São benchmarks de UX. O uso de GitHub/Product Hunt não habilita uma integração programática desses produtos.

## AppDeploy — limite constatado
O conector listou seis projetos MatVerse. A consulta de preflight de deployment recebeu `CREDITS_USAGE_LIMIT_REACHED`, com reset informado `2026-10-26T00:00:00Z`. **Nenhuma URL pública nova foi gerada**. Não tratar o HTML local como app já implantado.

O preflight foi repetido durante a aplicação da [matriz de saída de HOLD](PRANCHA_HOLD_EXIT_MATRIX.md) e devolveu o mesmo limite. Horário equivalente: 25/10/2026 às 21h de São Paulo. Não presumir liberação automática ou reconsultar antes do reset indicado.

## Próximas verificações
1. Concluir os bloqueios técnicos/editoriais da matriz; após o reset, reler as instruções da versão AppDeploy MCP 2.11.0 e confirmar disponibilidade.
2. Configurar hospedagem estática `frontend-only`, sem backend e sem segredos.
3. Publicar `index.html` somente após revisar conteúdo, licenciamento de mídia e ausência de dados pessoais.
4. Testar HTTP, áudio pt-BR, acesso por teclado, telas 360/768/1440, download de JSON e navegação offline.
5. Vincular URL/hash/release à referência canônica do Paper Vivo apenas após verificação independente.

## Segurança/epistemologia
Nenhum registro real do SymbioPet, credencial, assinatura Gate ou experimento do URANO está incorporado. A demonstração não constitui resultado clínico, autorizações de produção, RO-Crate validado ou evidência científica.

Esta declaração de escopo não equivale a auditoria completa de privacidade/licenças. O workflow valida exclusivamente o exemplo de cena e os casos negativos; o HTML v0.1 permanece separado, com QA de navegador/dispositivos e acessibilidade em HOLD. Não há adaptação automática do manifesto legado ao contrato v0.2.
