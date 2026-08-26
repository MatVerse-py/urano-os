# Provenance — URANO OSX (frontend)

```
provenance:
  original_frontend: unavailable
  implementation: clean_room_reconstruction
  source_basis: design_transcript + surviving specifications
  compatibility_target: URANO_OSX
  identity: NEW_IMPLEMENTATION
```

## What this is

The original `URANO OSX.html` and its supporting `actions.js`, `osx-field.js`,
`styles.css`, `views-*.js`, `viz.js` were authored in a Claude Design project
(`claude.ai/design/p/cb116f51-…`). That project's source bytes are not present
in this repository, and this session's environment could not pull them:
`DesignSync` requires interactive `/design-login`, which is unavailable here,
and no "Send to Claude Code Web" seed had landed in the workspace.

Rather than fabricate a file tree that *looks like* a recovered original, the
files under `urano/` are a **new, independently written implementation**,
built only from:

- the design conversation transcript pasted into this session (mode list,
  SceneSpec/Cube contract, Living Notebook golden path, epistemic visual
  grammar, ScientificObject v1 schema, six-axis reduction, etc.), and
- the surviving backend in `src/urano_kernel/` (event runtime, Cassandra
  gate, memory gate, evidence pack), which this reconstruction treats as
  read-only ground truth and does not modify or reinterpret.

Nothing here should be cited as evidence of what the original Claude Design
project contained byte-for-byte. It is a specification-compatible rebuild,
not a recovery.

## Status ledger

| Layer | State |
|---|---|
| `urano_kernel` backend | `PRESENT` (unmodified, pre-existing) |
| Original OSX frontend source | `SOURCE_NOT_RECOVERED` |
| DesignSync import | `BLOCKED_BY_INTERACTIVE_AUTH` |
| Claude Design project bytes | `NOT_AVAILABLE_IN_WORKSPACE` |
| This `urano/` tree | `CLEAN_ROOM_RECONSTRUCTION` (vNext, new identity) |

## Recovering the real original

If the original files ever become available (export, ZIP, a repo, or a
successful `DesignSync` pull after `/design-login`), they should replace
this tree wholesale and this document should be updated to say so — this
reconstruction should not be quietly merged with recovered bytes and
presented as continuous history.

## Kernel Bridge (one real traversal, not simulation)

`src/urano_kernel/bridge.py` is a new, additive file — it does not modify
any existing kernel module. It exposes the *existing* `perception`/`action`
event paths of `UranoKernel` over a local HTTP API and serves this repo as
static files, so the OSX Surface's "Kernel Bridge" panel can perform one
real traversal end to end:

```
OSX intent input
  -> POST /api/perceive
  -> EventRuntime.emit("perception", payload)
  -> CassandraGate.perceive()          (real validation)
  -> MemoryGate.append()               (real sha256 hash-chain entry)
  -> EvidencePack.add()                (real evidence record)
  -> receipt hash returned to the browser
  -> Cube pulses, Living Notebook records a real (OBSERVED_RESULT) cell
```

Run it from the repo root:

```
python3 -m src.urano_kernel.bridge
# then open http://localhost:8765/urano/URANO%20OSX.html
```

Opening `URANO OSX.html` directly (`file://`) still works for everything
except this panel, which will honestly report `KERNEL · offline`.

This bridge does **not** implement an Ω-Gate, authority/authorization
layer, or an Organism/Organs/Tools/Skills model — those remain design
proposals, not code. It exposes exactly the `perceive`/`act` paths that
already existed in `kernel.py`, nothing more. Do not read its presence as
those larger structures being built.

## Sample data disclosure

Views in this build (claim dependency graph, negative results, publication
projection chips) render **illustrative sample data** to demonstrate the
contract shape. None of it is wired to a real registry, arXiv/Zenodo/ORCID
account, or reproduced experiment. Sample nodes are labeled accordingly in
the UI; treat anything not explicitly marked `OBSERVED_RESULT` as a mockup.
