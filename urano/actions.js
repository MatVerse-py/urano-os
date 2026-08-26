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

    // kernel bridge — the one real (non-simulated) traversal into
    // src/urano_kernel/ via `python3 -m src.urano_kernel.bridge`.
    // Offline by default; never fabricates a receipt if unreachable.
    var KERNEL_BASE = global.location.origin.startsWith("http")
      ? global.location.origin
      : "http://localhost:8765";
    var kernelOnline = false;

    function setKernelStatus(text, cls) {
      refs.kernelStatus.textContent = "KERNEL · " + text;
      refs.kernelStatus.className = "pill " + cls;
    }

    function pollKernelState() {
      fetch(KERNEL_BASE + "/api/state")
        .then(function (r) {
          if (!r.ok) throw new Error("bad status");
          return r.json();
        })
        .then(function (data) {
          kernelOnline = true;
          setKernelStatus(
            "online · chain " + data.state.chain_length,
            "state-ok"
          );
        })
        .catch(function () {
          kernelOnline = false;
          setKernelStatus("offline", "state-hold");
        });
    }
    pollKernelState();
    var kernelPollId = global.setInterval(pollKernelState, 5000);

    refs.kernelForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var text = refs.kernelInput.value.trim();
      if (!text) return;
      refs.kernelInput.disabled = true;

      fetch(KERNEL_BASE + "/api/perceive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload: text }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          var ok = data.ok && data.memory_appended;
          var cell = {
            type: "kernel",
            text:
              'Kernel real: "' +
              text +
              '" → ' +
              data.result +
              (ok ? "" : " (não anexado à hash-chain)"),
            epistemicClass: ok ? "OBSERVED_RESULT" : "STATE_VISUALIZATION",
            mode: spec.mode,
            status: ok ? "kernel_real" : "kernel_fail",
            receiptHash: data.receipt_hash,
          };
          cells.push(cell);
          viewsOSX.appendCell(refs.cellsEl, cell);
          if (ok) {
            cube.pulse();
            refs.epistemicChip.textContent = "OBSERVED_RESULT";
            refs.epistemicChip.dataset.class = "OBSERVED_RESULT";
            global.setTimeout(function () {
              refs.epistemicChip.textContent = spec.epistemicClass;
              refs.epistemicChip.dataset.class = spec.epistemicClass;
            }, 1400);
          }
          pollKernelState();
        })
        .catch(function () {
          var cell = {
            type: "kernel",
            text: 'Kernel real: "' + text + '" → bridge unreachable (offline)',
            epistemicClass: "STATE_VISUALIZATION",
            mode: spec.mode,
            status: "kernel_fail",
          };
          cells.push(cell);
          viewsOSX.appendCell(refs.cellsEl, cell);
        })
        .finally(function () {
          refs.kernelInput.disabled = false;
          refs.kernelInput.value = "";
        });
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
        global.clearInterval(kernelPollId);
      },
    };
  }

  OSX.actions = { initOSXSurface: initOSXSurface };
})(window);
