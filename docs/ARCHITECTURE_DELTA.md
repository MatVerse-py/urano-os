# Architecture delta

Existing core: Event Runtime -> Cassandra Gate -> Memory Gate -> Evidence Pack.

Spatial extension proposed by this branch:

```text
Human / device input
  -> InteractionIntent
  -> Cassandra interpretation
  -> URANO ResearchState
  -> Scene Compiler
  -> SpatialSceneSpec
  -> Web / visionOS / OpenXR renderer
```

This extension is additive. It does not replace the Operational Core and does not make the visual layer authoritative over evidence, memory, policy or execution.
