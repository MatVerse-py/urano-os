/* URANO OSX — actions.js
 * Wires DOM behavior for the OSX Surface: Cassandra intent -> SceneSpec,
 * mode buttons, the Cube/field animation loop, and transduction (click a
 * region of the field -> a candidate notebook cell, never auto-promoted
 * to evidence).
 * Clean-room reconstruction — see PROVENANCE.md
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});

  function initOSXSurface(refs) {
    var viz = OSX.viz;
    var field = OSX.field;
    var viewsOSX = OSX.viewsOSX;

    var cube = viz.createCubeController(refs.cube);
    var fieldRenderer = viz.createFieldRenderer(refs.canvas);
    var spec = field.idleSpec();
    var rotating = true;
    var cells = [];

    viewsOSX.renderNotebookEmpty(refs.cellsEl);

    function setActiveModeButton(mode) {
      Object.keys(refs.modeButtons).forEach(function (m) {
        refs.modeButtons[m].classList.toggle("active", m === mode);
      });
    }

    function applySpec(nextSpec) {
      spec = nextSpec;
      refs.epistemicChip.textContent = spec.epistemicClass;
      refs.epistemicChip.dataset.class = spec.epistemicClass;
      setActiveModeButton(spec.mode);
      cube.setMorph(spec.morph);
    }

    applySpec(spec);

    // mode buttons: explicit override of Cassandra's inference
    Object.keys(refs.modeButtons).forEach(function (mode) {
      refs.modeButtons[mode].addEventListener("click", function () {
        applySpec(field.buildSceneSpec(refs.input.value, { mode: mode }));
      });
    });

    // cassandra intent bar
    refs.form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var text = refs.input.value.trim();
      if (!text) return;
      var nextSpec = field.buildSceneSpec(text);
      applySpec(nextSpec);
      var cell = {
        type: "research",
        text: 'Cassandra interpretou: "' + text + '" → modo ' + nextSpec.mode,
        epistemicClass: nextSpec.epistemicClass,
        mode: nextSpec.mode,
        status: "note",
      };
      cells.push(cell);
      viewsOSX.appendCell(refs.cellsEl, cell);
    });

    // rotate toggle
    refs.rotateBtn.addEventListener("click", function () {
      rotating = !rotating;
      refs.rotateBtn.textContent = "Rotacionar: " + (rotating ? "on" : "off");
      refs.rotateBtn.classList.toggle("active", rotating);
    });

    // transduction: click the field -> candidate hypothesis cell
    refs.canvas.addEventListener("click", function (ev) {
      var rect = refs.canvas.getBoundingClientRect();
      var nx = (ev.clientX - rect.left) / rect.width;
      var ny = (ev.clientY - rect.top) / rect.height;
      var cell = {
        type: "hypothesis",
        text:
          "Região selecionada em (" +
          nx.toFixed(2) +
          ", " +
          ny.toFixed(2) +
          ") sob modo " +
          spec.mode +
          " — candidata a hipótese, não executada.",
        epistemicClass: spec.epistemicClass,
        mode: spec.mode,
        status: "candidate_not_executed",
      };
      cells.push(cell);
      viewsOSX.appendCell(refs.cellsEl, cell);
    });

    // animation loop
    var lastT = performance.now();
    var raf;
    function tick(now) {
      var dt = Math.min(0.1, (now - lastT) / 1000);
      lastT = now;
      var facing = cube.step(rotating ? dt : 0, spec.motion);
      refs.readout.textContent = "FACE · " + facing;
      fieldRenderer.draw(spec, now / 1000);
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);

    return {
      unmount: function () {
        if (raf) cancelAnimationFrame(raf);
      },
    };
  }

  OSX.actions = { initOSXSurface: initOSXSurface };
})(window);
