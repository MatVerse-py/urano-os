# URANO Spatial App v0.1.0

## Constitutional split

- **Cassandra** interprets human intent and structures an `IntentPlan`.
- **URANO** owns the scientific `ResearchState` and changes it only through observed/authorized scientific operations.
- **SymbiOS** executes authorized capabilities. It is not the source of scientific truth.
- **SpatialSceneSpec** is a projection contract, never a source of evidence.
- **Adapters** render scenes and emit `InteractionIntent`; they do not silently mutate scientific state.

## Data flow

```text
Human input
  -> InteractionIntent
  -> Cassandra interpretation
  -> URANO ResearchState
  -> Scene Compiler
  -> SpatialSceneSpec
  -> Web | visionOS | OpenXR renderer
```

## Sovereignty

Capabilities are allowed by locality:

- SOVEREIGN: LOCAL only
- HYBRID: LOCAL + PRIVATE
- CLOUD: LOCAL + PRIVATE + PUBLIC_API

The renderer visualizes policy consequences; it does not enforce them. Enforcement belongs before invocation.

## Epistemic visual classes

`STATE_VISUALIZATION`, `SEMANTIC_MAP`, `SPECULATIVE_DREAM`, `OBSERVED_RESULT`, `GENERATIVE_METAPHOR`.

A generated visual must never be promoted to observed evidence solely because it is rendered.
