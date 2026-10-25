# Prancha MatVerse Runtime — contrato de apresentação viva v0.2 (proposta)

**Status:** SPEC_CANDIDATE / DEMO_ONLY · **Data:** 2026-10-25  
**Escopo deste PR:** documentação e contrato demonstrativo. Não altera kernel, Memory Gate, Cassandra Gate, assinaturas, políticas ou APIs existentes.

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

Ver `docs/examples/prancha-scene-demo.v1.json`. Campos críticos: `scene_id`, `source_ref`, `status`, `claims`, `evidence_refs`, `narration`, `content`, `authority`. `status=DEMO_ONLY` implica evidência não operacional. `release_receipt=null` não equivale a aprovação.

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
