/* URANO OSX — views-mesh.js
 * Organism Mesh: Kernel (surviving backend) + OSX (this reconstruction),
 * shown side by side with an explicit, unflattering status table. This
 * view exists specifically so the provenance gap is never hidden behind
 * a working UI.
 * Clean-room reconstruction — see PROVENANCE.md
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});

  var KERNEL_MODULES = [
    "event_runtime.py — orquestração de intenções / eventos",
    "cassandra_gate.py — validação de percepções / interface",
    "memory_gate.py — memória causal, encadeamento de hashes",
    "evidence_pack.py — coleta e selagem de evidência",
    "kernel.py — composição do runtime",
  ];

  var OSX_MODULES = [
    "Organism — presença persistente do Cubo",
    "Organs — modos (FOCUS/PRESENCE/ANALYSIS/DREAM/LAB/RITUAL)",
    "Tools — SceneSpec engine (osx-field.js)",
    "Skills — views (osx / science / mesh)",
    "Living Notebook — continuidade causal da investigação",
    "Cube — identidade topológica persistente",
    "Visualization — field + claim-graph renderers (viz.js)",
  ];

  var STATUS_ROWS = [
    ["URANO_BACKEND", "PRESENT", "state-ok"],
    ["URANO_FRONTEND (original)", "SOURCE_NOT_RECOVERED", "state-bad"],
    ["URANO_FRONTEND (this build)", "CLEAN_ROOM_RECONSTRUCTION", "state-hold"],
    ["DESIGNSYNC_IMPORT", "BLOCKED_BY_INTERACTIVE_AUTH", "state-bad"],
    ["CLAUDE_DESIGN_SOURCE", "NOT_AVAILABLE_IN_WORKSPACE", "state-bad"],
    ["FRONTEND_RECONSTRUCTION_FROM_PROSE", "DECLARED_NOT_ORIGINAL", "state-warn"],
  ];

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function mount(root) {
    root.innerHTML = "";
    root.appendChild(el("h1", "view-title", "Organism Mesh"));
    root.appendChild(
      el(
        "p",
        "view-lede",
        "URANO = Kernel (runtime sobrevivente) hospeda OSX (paradigma de " +
          "interface). Não são a mesma coisa — URANO é o domínio científico, " +
          "OSX é a superfície sensorial sobre ele."
      )
    );

    var columns = el("div", "mesh-columns");

    var kernelBox = el("div", "panel mesh-box");
    kernelBox.appendChild(el("h2", null, "Kernel — src/urano_kernel/"));
    var kUl = document.createElement("ul");
    KERNEL_MODULES.forEach(function (m) {
      kUl.appendChild(el("li", null, m));
    });
    kernelBox.appendChild(kUl);
    columns.appendChild(kernelBox);

    var osxBox = el("div", "panel mesh-box");
    osxBox.appendChild(el("h2", null, "OSX — urano/"));
    var oUl = document.createElement("ul");
    OSX_MODULES.forEach(function (m) {
      oUl.appendChild(el("li", null, m));
    });
    osxBox.appendChild(oUl);
    columns.appendChild(osxBox);

    root.appendChild(columns);

    var statusPanel = el("div", "panel");
    statusPanel.appendChild(el("h2", null, "Status ledger"));
    var table = document.createElement("table");
    table.className = "status-table";
    var thead = document.createElement("thead");
    var headRow = document.createElement("tr");
    headRow.appendChild(el("th", null, "layer"));
    headRow.appendChild(el("th", null, "state"));
    thead.appendChild(headRow);
    table.appendChild(thead);
    var tbody = document.createElement("tbody");
    STATUS_ROWS.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.appendChild(el("td", "key", row[0]));
      var stateTd = document.createElement("td");
      stateTd.appendChild(el("span", "pill " + row[2], row[1]));
      tr.appendChild(stateTd);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    statusPanel.appendChild(table);

    var note = el(
      "p",
      "view-lede",
      "Detalhe completo em "
    );
    var link = document.createElement("a");
    link.href = "PROVENANCE.md";
    link.textContent = "urano/PROVENANCE.md";
    link.className = "mono";
    note.appendChild(link);
    note.style.marginTop = "12px";
    statusPanel.appendChild(note);

    root.appendChild(statusPanel);
  }

  OSX.viewsMesh = { mount: mount };
})(window);
