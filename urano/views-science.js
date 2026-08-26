/* URANO OSX — views-science.js
 * ScientificObject v1: four clean axes (identity/epistemic/reproduction/
 * publication), a claim dependency graph, negative results as first-class
 * objects, and publication projections that are never treated as replaced
 * services. All data on this view is illustrative sample data — see
 * PROVENANCE.md.
 * Clean-room reconstruction — see PROVENANCE.md
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});
  var viz = OSX.viz;

  var AXES = [
    {
      key: "identity",
      states: ["artifact_id", "version", "authors", "hash", "commit", "lineage"],
      current: "lineage",
    },
    {
      key: "epistemic",
      states: [
        "SPECIFIED", "IMPLEMENTED", "EXECUTED", "OBSERVED",
        "SUPPORTED", "CONTRADICTED", "RETRACTED",
      ],
      current: "OBSERVED",
    },
    {
      key: "reproduction",
      states: [
        "NOT_AVAILABLE", "LOCAL_REPLAY", "CLEAN_ENV_REPLAY",
        "INDEPENDENT_REPLAY", "MULTI_SITE_REPLICATION",
      ],
      current: "CLEAN_ENV_REPLAY",
    },
    {
      key: "publication",
      states: [
        "PRIVATE", "INTERNAL", "PREPRINT_READY",
        "PUBLIC", "SUPERSEDED", "WITHDRAWN",
      ],
      current: "INTERNAL",
    },
  ];

  var SAMPLE_GRAPH = {
    nodes: [
      { id: "C1", x: 0.5, y: 0.12, state: "CONTRADICTED" },
      { id: "C4", x: 0.3, y: 0.42, state: "REVIEW_REQUIRED" },
      { id: "C5", x: 0.7, y: 0.42, state: "REVIEW_REQUIRED" },
      { id: "C9", x: 0.18, y: 0.82, state: "REVIEW_REQUIRED" },
      { id: "C10", x: 0.42, y: 0.82, state: "REVIEW_REQUIRED" },
      { id: "C12", x: 0.7, y: 0.82, state: "SUPPORTED" },
    ],
    edges: [
      { from: "C1", to: "C4" },
      { from: "C1", to: "C5" },
      { from: "C4", to: "C9" },
      { from: "C4", to: "C10" },
      { from: "C5", to: "C12" },
    ],
  };

  var NEGATIVE_RESULTS = [
    {
      id: "NR-07",
      hypothesis: "Reprodução independente confirmaria C1 em ambiente limpo",
      protocol: "CLEAN_ENV_REPLAY, seed fixa, 3 execuções",
      observed: "Divergência > tolerância declarada em 2 de 3 execuções",
      implication: "C1 rebaixado; C4/C5 marcados REVIEW_REQUIRED",
    },
    {
      id: "NR-11",
      hypothesis: "Dataset alternativo sustentaria C12 sem ajuste de protocolo",
      protocol: "LOCAL_REPLAY sobre dataset B",
      observed: "Resultado consistente com C12 — não refuta",
      implication: "Preservado como tentativa registrada, não como evidência nova",
    },
  ];

  var PROJECTIONS = [
    { name: "arXiv", role: "frente científica pública", status: "NOT_CONFIGURED" },
    { name: "Zenodo", role: "preservação + DOI", status: "NOT_CONFIGURED" },
    { name: "ORCID", role: "identidade do autor", status: "NOT_CONFIGURED" },
    { name: "GitHub", role: "código + replay", status: "NOT_CONFIGURED" },
    { name: "Hugging Face", role: "dados/modelos", status: "NOT_CONFIGURED" },
  ];

  var SAMPLE_OBJECT = {
    identity: {
      artifact_id: "MX-SAMPLE-0001",
      version: "0.1.0",
      hash: "sha256:… (illustrative)",
      supersedes: null,
    },
    epistemic: { state: "OBSERVED" },
    reproduction: { state: "CLEAN_ENV_REPLAY" },
    publication: { state: "INTERNAL" },
    governance: {
      policy: "none_applied",
      decision: "n/a",
      scope: "n/a",
      timestamp: null,
    },
  };

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function mount(root) {
    root.innerHTML = "";
    root.appendChild(el("h1", "view-title", "ScientificObject v1"));
    root.appendChild(
      el(
        "p",
        "view-lede",
        "Um contrato de quatro eixos atravessando URANO → MARXIV → Paper Vivo → " +
          "Registry → Projeções. Governança é reportada, não misturada ao estado " +
          "epistemológico. Dados desta página são ilustrativos — ver PROVENANCE.md."
      )
    );

    // axes
    var axesPanel = el("div", "panel");
    axesPanel.appendChild(el("h2", null, "Identity · Epistemic · Reproduction · Publication"));
    var grid = el("div", "axes-grid");
    AXES.forEach(function (axis) {
      var card = el("div", "axis-card");
      card.appendChild(el("h3", null, axis.key));
      var states = el("div", "axis-states");
      axis.states.forEach(function (s) {
        states.appendChild(
          el("div", "axis-state" + (s === axis.current ? " current" : ""), s)
        );
      });
      card.appendChild(states);
      grid.appendChild(card);
    });
    axesPanel.appendChild(grid);
    root.appendChild(axesPanel);

    // claim graph
    var graphPanel = el("div", "panel");
    graphPanel.appendChild(el("h2", null, "Claim Dependency Graph (sample)"));
    var graphWrap = el("div", "claim-graph-wrap");
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 480 260");
    graphWrap.appendChild(svg);
    graphPanel.appendChild(graphWrap);
    root.appendChild(graphPanel);

    var t0 = performance.now();
    var raf;
    function tick() {
      var t = (performance.now() - t0) / 1000;
      viz.renderClaimGraph(svg, SAMPLE_GRAPH, t);
      raf = requestAnimationFrame(tick);
    }
    tick();

    // negative results
    var nrPanel = el("div", "panel");
    nrPanel.appendChild(el("h2", null, "Negative Results (first class, sample)"));
    var cards = el("div", "result-cards");
    NEGATIVE_RESULTS.forEach(function (nr) {
      var card = el("div", "result-card");
      card.appendChild(el("h4", null, nr.id));
      var dl = document.createElement("dl");
      [
        ["hypothesis", nr.hypothesis],
        ["protocol", nr.protocol],
        ["observed", nr.observed],
        ["implication", nr.implication],
      ].forEach(function (pair) {
        dl.appendChild(el("dt", null, pair[0]));
        dl.appendChild(el("dd", null, pair[1]));
      });
      card.appendChild(dl);
      cards.appendChild(card);
    });
    nrPanel.appendChild(cards);
    root.appendChild(nrPanel);

    // publication projections
    var projPanel = el("div", "panel");
    projPanel.appendChild(el("h2", null, "Publication Projections — RO-Crate 1.3 (none replace another)"));
    var list = el("div", "projection-list");
    PROJECTIONS.forEach(function (p) {
      var chip = el("div", "projection-chip");
      chip.appendChild(el("strong", null, p.name));
      chip.appendChild(el("span", "mono", p.role));
      chip.appendChild(el("span", "pill state-hold", p.status));
      list.appendChild(chip);
    });
    projPanel.appendChild(list);
    root.appendChild(projPanel);

    // json contract
    var jsonPanel = el("div", "panel");
    jsonPanel.appendChild(el("h2", null, "scientific-object.json"));
    var pre = el("pre", "json-preview", JSON.stringify(SAMPLE_OBJECT, null, 2));
    jsonPanel.appendChild(pre);
    root.appendChild(jsonPanel);

    return {
      unmount: function () {
        if (raf) cancelAnimationFrame(raf);
      },
    };
  }

  OSX.viewsScience = { mount: mount };
})(window);
