/* URANO OSX — osx-field.js
 * SceneSpec engine. Cassandra never emits shaders/graphics commands
 * directly — it interprets intent text into a validated SceneSpec, and
 * viz.js is the only thing that renders it.
 * Clean-room reconstruction — see PROVENANCE.md
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});
  var viz = OSX.viz;

  var MODES = ["FOCUS", "PRESENCE", "ANALYSIS", "DREAM", "LAB", "RITUAL"];

  var MODE_KEYWORDS = {
    ANALYSIS: [
      "conflito", "conflict", "fragmentad", "contradi", "mapa", "map",
      "relação", "relacoes", "relations", "onde existe",
    ],
    DREAM: [
      "sonho", "dream", "explorar sem concluir", "imagin", "surreal",
      "possível", "possibilidade", "metáfora", "metafora",
    ],
    LAB: [
      "testar", "test", "experimento", "experiment", "laboratório",
      "laboratorio", "hipótese", "hipotese", "protocolo", "rodar", "simular",
    ],
    RITUAL: [
      "converg", "cristaliz", "congelar", "freeze", "concluir", "fechar",
      "consolidar",
    ],
    PRESENCE: ["presença", "presence", "respirando", "silêncio", "silencio"],
  };

  var MODE_PRESETS = {
    FOCUS: { density: 0.14, motion: 0.12, whirl: 0.05, morph: 0.02 },
    PRESENCE: { density: 0.22, motion: 0.08, whirl: 0.12, morph: 0.05 },
    ANALYSIS: { density: 0.55, motion: 0.35, whirl: 0.3, morph: 0.25 },
    DREAM: { density: 0.85, motion: 0.6, whirl: 0.55, morph: 0.75 },
    LAB: { density: 0.4, motion: 0.4, whirl: 0.18, morph: 0.15 },
    RITUAL: { density: 0.3, motion: 0.5, whirl: 0.85, morph: 0.35 },
  };

  var MODE_EPISTEMIC_DEFAULT = {
    FOCUS: "STATE_VISUALIZATION",
    PRESENCE: "STATE_VISUALIZATION",
    ANALYSIS: "SEMANTIC_MAP",
    DREAM: "SPECULATIVE_DREAM",
    LAB: "STATE_VISUALIZATION",
    RITUAL: "GENERATIVE_METAPHOR",
  };

  function inferMode(text) {
    var t = (text || "").toLowerCase();
    if (!t.trim()) return "PRESENCE";
    for (var i = 0; i < MODES.length; i++) {
      var mode = MODES[i];
      var kws = MODE_KEYWORDS[mode];
      if (!kws) continue;
      for (var j = 0; j < kws.length; j++) {
        if (t.indexOf(kws[j]) !== -1) return mode;
      }
    }
    return "FOCUS";
  }

  // deterministic: same intent text -> same seed -> same scene, always.
  function buildSceneSpec(intentText, opts) {
    opts = opts || {};
    var mode = opts.mode || inferMode(intentText);
    var preset = MODE_PRESETS[mode] || MODE_PRESETS.FOCUS;
    var seed = viz.hashStr((intentText || "idle") + "::" + mode);
    var rnd = viz.mulberry32(seed);
    var jitter = function (base, spread) {
      return Math.max(0, Math.min(1, base + (rnd() - 0.5) * spread));
    };

    return {
      seed: seed,
      mode: mode,
      epistemicClass: opts.epistemicClass || MODE_EPISTEMIC_DEFAULT[mode],
      density: jitter(preset.density, 0.12),
      motion: jitter(preset.motion, 0.12),
      whirl: jitter(preset.whirl, 0.12),
      morph: jitter(preset.morph, 0.1),
      intent: intentText || "",
      createdAt: new Date().toISOString(),
    };
  }

  function idleSpec() {
    return buildSceneSpec("", { mode: "PRESENCE" });
  }

  OSX.field = {
    MODES: MODES,
    MODE_EPISTEMIC_DEFAULT: MODE_EPISTEMIC_DEFAULT,
    inferMode: inferMode,
    buildSceneSpec: buildSceneSpec,
    idleSpec: idleSpec,
  };
})(window);
