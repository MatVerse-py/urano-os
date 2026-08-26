# URANO OS

O **URANO OS** é um organismo digital verificável, construído sobre os princípios de autopoiese e integridade causal. Este repositório contém o **Operational Core v0.5**, responsável pelo runtime, processamento de eventos e gestão de evidências.

## Componentes do Core v0.5
- **Event Runtime**: Orquestração de intenções e fluxos orientados a eventos.
- **Cassandra Gate**: Validação de percepções e interface de voz/alerta.
- **Memory Gate**: Memória causal com encadeamento de hashes.
- **Evidence Pack**: Coleta e selagem de provas de execução.

## Dependências
Este sistema depende fundamentalmente do [urano-digital-life-contract](./contracts), que atua como o cartório de vida digital e registro de twins.

## Frontend (OSX)
A superfície visual — [`urano/URANO OSX.html`](./urano/URANO%20OSX.html) — é um
**clean-room reconstruction**: o frontend original (Claude Design) não pôde
ser recuperado neste ambiente, então esta é uma reimplementação nova,
compatível com a especificação conhecida, não uma recuperação de bytes
originais. Ver [`urano/PROVENANCE.md`](./urano/PROVENANCE.md) para o
detalhamento completo e a distinção de linhagem.

## Como Executar
```bash
python3 -m src.urano_kernel.kernel
```

---
*URANO OS: Evento → Memória → Decisão → Prova → Replay*
