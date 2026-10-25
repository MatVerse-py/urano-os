# Prancha MatVerse Runtime — contrato de apresentação viva v0.2 (proposta)

**Status:** SPEC_CANDIDATE / DEMO_ONLY · **Data:** 2026-10-25  
**Escopo deste PR:** documentação, perfil demonstrativo e verificações isoladas desse perfil. Não altera kernel, Memory Gate, Cassandra Gate, assinaturas, políticas ou APIs existentes.

## Objetivo

Transformar a Prancha MatVerse de suporte gráfico estático em uma **projeção navegável** do objeto científico/operacional, com cinco lentes sobre a mesma referência:
1. Narrativa e audiodescrição, inclusive offline;
2. Arquitetura multiescala (OSX/Cubo);
3. Laboratório/URANO (experimentos explícitos, não simulados como verdade);
4. Paper Vivo/MARXIV (claim, evidência, versão, citação, resultado negativo);
5. Mapa de integrações de produção e publicação.

A apresentação não decide autorização nem comprova experimentos por si só. O core URANO permanece responsável por seu fluxo `evento → memória → decisão → prova → replay`. A Prancha consome somente *artefatos autorizados e versionados*, com origem e estado epistêmico preservados.

## Fronteiras de autoridade

| Componente | Responsabilidade | Não pode fazer pela Prancha |
|---|---|---|
| ASTRA+ / Cassandra | Propor cenas e interpretações | Emitir prova, autorização ou resultado sem fonte |
| URANO | Protocolos, execuções, observações e replay | Confundir demonstração em navegador com experimento executado |
| Ω-Gate | Autorizar ou bloquear ações segundo contrato/política | Herdar autoridade de uma animação ou texto |
| Evidence Pack / Witness | Referências, digestos e recibos reais | Tratar arquivos JSON ilustrativos como recibos |
| MARXIV + Paper Vivo | Vincular claims, dependências, versão e eventual empacotamento | Declarar RO-Crate validado ou revisão por pares sem verificação |
| Prancha | Renderizar narrativa, dados e estados acessíveis | Alterar o estado canônico ou substituir a checagem de acesso |

## Contrato mínimo de cena

Ver [exemplo](examples/prancha-scene-demo.v1.json) e [esquema demonstrativo](schemas/prancha-scene-demo.v1.schema.json). Campos críticos: `scene_id`, `source_ref`, `status`, `claims`, `claims[*].evidence_refs`, `narration`, `content`, `authority`. `status=DEMO_ONLY` implica evidência não operacional. `authority.release_receipt_ref=null` não equivale a aprovação.

O perfil local aceita `HYPOTHESIS` (hipótese), `HOLD` (pendência) e `DEMO` (ilustração) nos claims. São estados distintos; nenhum é convertido em FATO ou autorização. Exige `may_execute=false`, referências Gate/receipt nulas, dados sintéticos e evidências vazias. `HYPOTHESIS` permanece no exemplo; não é um sinônimo de HOLD.

O validador `tools/prancha_demo.py` rejeita campos desconhecidos em todos os objetos, chaves JSON duplicadas, tipos incorretos, versões não suportadas, fontes fora do namespace fictício, claims repetidos, payloads acima de 65.536 bytes e profundidade superior a 16. Aplica somente os keywords usados pelo esquema incluído; não é um motor JSON Schema geral e rejeita keywords desconhecidos. Não importa nem chama o kernel.

### Compatibilidade explícita de versões

| Objeto | Versão | O que foi verificado |
|---|---|---|
| Contrato documental | v0.2 / candidato | Fronteiras e perfil demonstrativo |
| Exemplo de cena | `matverse.prancha.scene.v1-demo`, `version=0.2.0` | Validação do perfil local e casos negativos |
| HTML independente | v0.1 | Hash, sintaxe e inspeção estática; QA em navegador HOLD |
| Exportação atual do HTML | `matverse.prancha.presentation.v0.1-demo` | Formato legado, **não** validado pelo perfil de cena |
| Exportação ScientificObject | `matverse.scientific_object.demo.v0.1` | JSON ilustrativo, **não** RO-Crate nem receipt |

Não há adaptador automático entre o manifesto de apresentação e o de cena. O CI do exemplo não valida a exportação do HTML. Ver [matriz de saída de HOLD](PRANCHA_HOLD_EXIT_MATRIX.md) para a publicação demonstrativa e os requisitos operacionais que permanecem pendentes.

## Fluxo proposto de plugins

- **GitHub**: versionamento, issues, CI, PR de revisão, *não* validação científica por simples existência.
- **Product Hunt**: pesquisa de benchmarks de UX; Vizzu (storytelling quantitativo), Marimo (notebooks reprodutíveis), Faces (apresentações exploráveis); inspirações, não dependências.
- **AppDeploy**: hospedar versão estática e responsiva da Prancha, com transcrição, narração opcional e manifesto de origem; deploy depende de orçamento e testes, sem segredos no frontend.
- **Figma / Gamma / Descript**: opções posteriores para design, narrativa e audiovisual, exportadas via `AssetRef`; plugins não recebem acesso direto à autoridade do Gate.

## Critérios de aceitação para integração real (não cumpridos neste PR)

1. `SceneManifest` passa por validação de esquema, versão, tamanhos e autorização; dados desconhecidos são rejeitados.
2. Todo claim tem fonte explícita e estado FATO/INFERÊNCIA/HOLD/DEMO, sem promover HOLD por apresentação.
3. Decisões executáveis exigem validação do Gate no backend; cliente somente apresenta decisão já autorizada.
4. EvidenceRefs apontam para digestos/recibos verificáveis; replay testado independentemente.
5. UX validada em telefone/tablet/desktop, contraste, teclado, narração e redução de movimento.
6. Nenhum segredo, dado animal real ou conteúdo privado em bundle público.
7. MARXIV: pacote RO-Crate/JSON-LD apenas após validação do esquema e dependências de claim.

## Caso demonstrativo

SymbioPet — Ajud. Um Pet → GroomCare → Atlas → PetMesh → Overlay Pet. Todos os registros de Lua são fictícios. Registro visual não persiste no backend e não fornece permissões canônicas. Fonte histórica do Ajud. Um Pet ainda depende de revisão de Lavínia.

## Publicação

A versão de apresentação v0.1 existe como artefato HTML independente com áudio incorporado, mas **não foi incorporada ao repositório** por este PR. O AppDeploy informou bloqueio de implantação por limite semanal no momento da preparação (reset fornecido pelo provedor: 2026-10-26T00:00:00Z). Não divulgar URL nova antes de confirmação de deploy e QA.
