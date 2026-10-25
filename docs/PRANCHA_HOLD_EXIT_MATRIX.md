# Prancha v0.2 — matriz de saída de HOLD

Data: 25/10/2026 (São Paulo). Escopo: publicação de uma demonstração estática.
Estado: **SPEC_CANDIDATE / DEMO_ONLY / DEPLOY_HOLD**.
Esta matriz não concede autorização, promove claims ou libera produção.

## Estado executado

- Snapshot inicial do PR #6: `58b4fcb8331245182e5643e976e864c01b53da2d`.
- O HTML original foi recuperado e seu hash/tamanho conferidos: SHA-256 `9bae870fefb63c079a5afa632e1a64d5d0b0d6c2a25c61f8f31efb68fc67ba1e`, 4.668.964 bytes. Nenhuma edição foi feita nesse arquivo.
- Dez testes locais do perfil, incluindo entradas negativas, aprovados. Isso não valida contratos operacionais, a exportação legada ou a publicação.
- Auditoria estática reproduzida: sintaxe JavaScript, seis PNG/seis MP3 embutidos, IDs únicos, transcrição pt-BR e coerência entre os claims/módulos da UI e do manifesto legado. [Resultado completo](prancha-demo-static-audit.json).
- Ausência de recursos remotos automáticos declarados e de indicadores das APIs de rede examinadas. Isso não substitui observação de tráfego em navegador, revisão de privacidade ou licenças.
- Navegador local: BLOQUEADO. Playwright disponível, Chromium ausente; o download não forneceu arquivo ZIP válido. Nenhum teste visual, de áudio em navegador ou de dispositivo foi marcado PASS.
- AppDeploy: preflight repetido, resposta `CREDITS_USAGE_LIMIT_REACHED`; reset informado `2026-10-26T00:00:00Z` = 25/10/2026 às 21h de São Paulo. Nenhum deploy solicitado ou URL nova gerada.
- CI do perfil: workflow adicionado; confirmar a execução do commit revisado nos Actions. Um resultado local ou status de bot não encerra esse item. O workflow não recebe o HTML externo.

## Dependências da publicação demonstrativa

| ID | Frente | Estado nesta revisão | Saída exigida | Depende de |
|---|---|---|---|---|
| D0 | Escopo visual e rótulos | ESPECIFICADO | Exibir DEMO_ONLY de modo consistente nas telas e exportações; integrações e resultados ausentes continuam identificados | — |
| D1 | Identidade do HTML | CONCLUÍDO no original | Testar/publicar os mesmos bytes. Edições exigem novo hash e repetição dos checks afetados | D0 |
| D2 | Perfil de cena | PASS_LOCAL; integração com o HTML HOLD | Rodar esquema/perfil e negativos; manter tabela de compatibilidade. Não anunciar o HTML legado como consumidor v0.2 | D0 + D1 |
| D3 | Isolamento, conteúdo e mídias | PARCIAL | Revisar scripts/mídias/licenças, adequação da narrativa pública e observar tráfego: sem kernel/Gate, credenciais, dados privados ou escrita remota | D1 |
| D4 | CI | Workflow do perfil preparado | Execução real do job no commit revisado. QA do HTML é separado e vinculado ao hash; não herda o verde do perfil | D2 + D3 |
| D5 | UX e acessibilidade | HOLD, com achados de fonte | Corrigir achados abaixo e testar 360/768/1440, teclado, foco, contraste, áudio/transcrição, movimento reduzido e exportação. Desktop e telefone reais; tablet físico permanece HOLD se não testado | D1–D3 |
| D6 | Publicação e observação pública | BLOQUEADO pelo provedor | Após D4/D5, preflight disponível, frontend-only, mesmo artefato aprovado, HTTPS/HTTP, conteúdo servido, navegação, áudio, exportação e offline conferidos antes de divulgar URL | D4 + D5 + provedor |

Ordem: D0 → D1 → D2/D3 → D4/D5 → D6. Créditos podem ser consultados em paralelo. Não compensam falha técnica.

## Achados concretos no HTML v0.1

1. As cinco abas declaram `role=tab`, mas não têm `aria-controls`, associação a painéis nem roving tabindex. O handler global das setas controla slides quando o modo é story, inclusive quando o foco está nas abas. Implementar navegação de abas e delimitar o atalho de slides.
2. O selo superior de demo é ocultado abaixo de 720px; há avisos no rodapé e nas telas, mas falta uma identificação persistente e inequívoca de DEMO_ONLY em mobile.
3. Todo claim diferente de HOLD recebe a classe `status-pass`, inclusive arquitetura proposta. Separar estilo/estado de DEMO, hipótese e resultado verificado.
4. A exportação usa um schema de apresentação v0.1 com estados livres. Não converter automaticamente para `scene.v1-demo`; uma integração futura exige mapeamento explícito e teste da exportação resultante.
5. A narrativa é personalizada para Lavínia e menciona revisão histórica pendente. A versão pública precisa de revisão editorial; o material recuperado não contém comprovação de direitos de distribuição das mídias.

Estes são achados de leitura de código/conteúdo. Efeitos visuais, contraste medido e comportamento assistivo continuam não testados.

## HOLDs operacionais preservados

| Frente | Quando não bloqueia a demo | O que exige para sair de HOLD |
|---|---|---|
| Experimentos | Cenas identificadas como sintéticas, sem resultado científico executado | Protocolo, entradas, ambiente, resultados e reprodução independente |
| Autorização backend/Gate | Nenhum caminho operacional de execução ou acesso protegido | Integração e testes de autorização, negação, expiração e tentativa de contorno |
| Comprovantes ↔ claims | Fontes fictícias/vazias preservadas como tais | Referência real, integridade, correspondência semântica e versão verificadas |
| Contratos operacionais | Validação anunciada somente para o perfil demo | Esquemas canônicos e integração com consumidores reais |
| MARXIV / RO-Crate / JSON-LD | JSON divulgado como ilustrativo | Validação de pacote/esquema e dependências de claims |
| Dispositivos / acessibilidade ampla | Suporte anunciado somente às plataformas efetivamente testadas | Execução nas demais plataformas e avaliação assistiva ampliada |

## Reproduzir sem alterar o kernel

```sh
python3 -m unittest discover -s tests -p 'test_prancha_demo.py' -v
python3 tools/prancha_demo.py docs/examples/prancha-scene-demo.v1.json
python3 tools/audit_prancha_artifact.py /caminho/para/index.html --output /tmp/prancha-static.json
```

Python 3 e Node para a checagem de sintaxe do HTML; nenhum pacote Python externo. O terceiro comando exige o HTML original recuperado do pacote entregue e falha se hash/tamanho diferirem. Ele não executa scripts, não envia dados e não autoriza release. O HTML/mídias não foram copiados ao GitHub.

Conclusão: **PUBLICAÇÃO HOLD**. Perfil e identidade do artefato avançaram; navegador, dispositivos, acessibilidade, revisão de conteúdo/mídias e deploy continuam pendentes. O kernel e o submódulo de contratos permanecem idênticos ao snapshot inicial.
