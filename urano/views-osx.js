/* URANO OSX — views-osx.js
 * The OSX Surface: one continuous space, not a dashboard. Generative field
 * on top, Living Notebook below, Cassandra's intent bar crossing both.
 * Clean-room reconstruction — see PROVENANCE.md
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});
  var field = OSX.field;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function mount(root) {
    root.innerHTML = "";

    var h1 = el("h1", "view-title", "OSX Surface");
    var lede = el(
      "p",
      "view-lede",
      "Cassandra interpreta a intenção e produz um SceneSpec determinístico; " +
        "o Cubo e o campo generativo renderizam esse contrato — nunca código " +
        "gráfico arbitrário. Clique em uma região do campo para transduzir " +
        "em uma célula de hipótese no notebook."
    );
    root.appendChild(h1);
    root.appendChild(lede);

    var wrap = el("div", "osx-surface");
    root.appendChild(wrap);

    // mode bar
    var modeBar = el("div", "mode-bar");
    var modeButtons = {};
    field.MODES.forEach(function (m) {
      var b = el("button", "mode-btn", m);
      b.type = "button";
      b.dataset.mode = m;
      modeBar.appendChild(b);
      modeButtons[m] = b;
    });
    wrap.appendChild(modeBar);

    // field stage
    var stage = el("div", "field-stage");
    var canvas = document.createElement("canvas");
    stage.appendChild(canvas);

    var cubeStage = el("div", "cube-stage");
    var cube = el("div", "cube");
    cubeStage.appendChild(cube);
    stage.appendChild(cubeStage);

    var legend = el("div", "field-legend");
    var epistemicChip = el("span", "epistemic-chip", "STATE_VISUALIZATION");
    legend.appendChild(epistemicChip);
    stage.appendChild(legend);

    var readout = el("div", "field-readout mono", "FACE · RESEARCH");
    stage.appendChild(readout);

    wrap.appendChild(stage);

    // cassandra bar
    var bar = el("div", "cassandra-bar");
    var form = document.createElement("form");
    form.className = "cassandra-bar";
    form.style.flex = "1";
    form.style.display = "flex";
    form.style.gap = "8px";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder =
      'Fale com Cassandra — "mostre onde existe conflito", "testar esta lacuna", "quero explorar sem concluir"…';
    var submit = el("button", "submit", "Interpretar");
    submit.type = "submit";
    form.appendChild(input);
    form.appendChild(submit);
    wrap.appendChild(form);

    // rotate toggle row
    var toggleRow = el("div", "mode-bar");
    var rotateBtn = el("button", "mode-btn active", "Rotacionar: on");
    rotateBtn.type = "button";
    toggleRow.appendChild(rotateBtn);
    wrap.appendChild(toggleRow);

    // kernel bridge panel — the one real (non-simulated) traversal
    var kernelPanel = el("div", "panel kernel-panel");
    var kernelHead = el("div", "kernel-head");
    var kernelStatus = el("span", "pill state-hold", "KERNEL · checking…");
    kernelHead.appendChild(el("h2", null, "Kernel Bridge"));
    kernelHead.appendChild(kernelStatus);
    kernelPanel.appendChild(kernelHead);
    kernelPanel.appendChild(
      el(
        "p",
        "view-lede kernel-lede",
        "Traversal real, não simulada: percorre event_runtime → cassandra_gate → " +
          "memory_gate (hash-chain) → evidence_pack de src/urano_kernel/ via " +
          "python3 -m src.urano_kernel.bridge. Offline por padrão."
      )
    );
    var kernelForm = document.createElement("form");
    kernelForm.className = "cassandra-bar";
    var kernelInput = document.createElement("input");
    kernelInput.type = "text";
    kernelInput.placeholder = "payload de percepção para o kernel real…";
    var kernelSubmit = el("button", "submit", "Perceive →");
    kernelSubmit.type = "submit";
    kernelForm.appendChild(kernelInput);
    kernelForm.appendChild(kernelSubmit);
    kernelPanel.appendChild(kernelForm);
    wrap.appendChild(kernelPanel);

    // notebook
    var notebook = el("div", "notebook");
    var notebookHead = el("div", "notebook-head", "Living Notebook");
    notebook.appendChild(notebookHead);
    var cellsEl = el("div", "notebook-cells");
    notebook.appendChild(cellsEl);
    wrap.appendChild(notebook);

    return {
      root: root,
      wrap: wrap,
      canvas: canvas,
      cube: cube,
      modeButtons: modeButtons,
      epistemicChip: epistemicChip,
      readout: readout,
      form: form,
      input: input,
      rotateBtn: rotateBtn,
      cellsEl: cellsEl,
      kernelStatus: kernelStatus,
      kernelForm: kernelForm,
      kernelInput: kernelInput,
    };
  }

  function renderNotebookEmpty(cellsEl) {
    cellsEl.innerHTML = "";
    cellsEl.appendChild(
      el(
        "div",
        "notebook-empty",
        "Nenhuma célula ainda. Fale com Cassandra ou clique no campo para começar."
      )
    );
  }

  var STATUS_CLASS = {
    candidate_not_executed: "candidate",
    kernel_real: "kernel-real",
    kernel_fail: "kernel-fail",
  };

  var STATUS_FLAG_TEXT = {
    candidate_not_executed: "candidate_not_executed — not evidence",
    kernel_real: "OBSERVED_RESULT — real kernel traversal",
    kernel_fail: "kernel rejected — QUARANTINE/NULL, not appended",
  };

  function appendCell(cellsEl, cell) {
    var empty = cellsEl.querySelector(".notebook-empty");
    if (empty) empty.remove();

    var extraClass = STATUS_CLASS[cell.status] || "";
    var wrap = el("div", "cell" + (extraClass ? " " + extraClass : ""));
    var badge = el("div", "cell-badge", cell.type.toUpperCase());
    var body = el("div", "cell-body");
    var text = el("div", "cell-text", cell.text);
    var meta = el("div", "cell-meta mono");
    meta.appendChild(el("span", null, cell.epistemicClass));
    meta.appendChild(el("span", null, cell.mode));
    var flagText = STATUS_FLAG_TEXT[cell.status];
    if (flagText) {
      meta.appendChild(el("span", "flag-candidate", flagText));
    }
    if (cell.receiptHash) {
      meta.appendChild(el("span", null, "receipt:" + cell.receiptHash.slice(0, 12)));
    }
    body.appendChild(text);
    body.appendChild(meta);
    wrap.appendChild(badge);
    wrap.appendChild(body);
    cellsEl.insertBefore(wrap, cellsEl.firstChild);
  }

  OSX.viewsOSX = {
    mount: mount,
    renderNotebookEmpty: renderNotebookEmpty,
    appendCell: appendCell,
  };
})(window);
