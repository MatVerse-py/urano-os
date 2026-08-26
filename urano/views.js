/* URANO OSX — views.js
 * Router: mounts one view at a time into #main, builds the grouped
 * sidebar nav, and persists the last-open view for a standalone reload.
 * Clean-room reconstruction — see PROVENANCE.md
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});

  var VIEWS = [
    { id: "osx-surface", group: "CIÊNCIA", label: "OSX Surface" },
    { id: "scientific-object", group: "CIÊNCIA", label: "ScientificObject v1" },
    { id: "organism-mesh", group: "INFRAESTRUTURA", label: "Organism Mesh" },
  ];

  var STORAGE_KEY = "urano-osx:last-view";
  var THEME_KEY = "urano-osx:theme";

  function currentUnmount(state) {
    if (state.active && typeof state.active.unmount === "function") {
      state.active.unmount();
    }
    state.active = null;
  }

  function mountView(id, mainEl, navButtons, state) {
    currentUnmount(state);
    Object.keys(navButtons).forEach(function (vid) {
      navButtons[vid].classList.toggle("active", vid === id);
    });

    var result;
    if (id === "osx-surface") {
      var refs = OSX.viewsOSX.mount(mainEl);
      result = OSX.actions.initOSXSurface(refs);
    } else if (id === "scientific-object") {
      result = OSX.viewsScience.mount(mainEl);
    } else if (id === "organism-mesh") {
      OSX.viewsMesh.mount(mainEl);
      result = null;
    }
    state.active = result || null;

    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch (e) {
      /* standalone file:// or storage disabled — non-fatal */
    }
  }

  function buildSidebar(sidebarEl, mainEl, state) {
    var nav = document.createElement("nav");
    var navButtons = {};
    var lastGroup = null;

    VIEWS.forEach(function (view) {
      if (view.group !== lastGroup) {
        var label = document.createElement("div");
        label.className = "group-label";
        label.textContent = view.group;
        nav.appendChild(label);
        lastGroup = view.group;
      }
      var btn = document.createElement("button");
      btn.className = "nav-item";
      btn.type = "button";
      btn.textContent = view.label;
      btn.addEventListener("click", function () {
        mountView(view.id, mainEl, navButtons, state);
      });
      nav.appendChild(btn);
      navButtons[view.id] = btn;
    });

    sidebarEl.appendChild(nav);
    return navButtons;
  }

  function initTheme(toggleBtn) {
    var saved;
    try {
      saved = localStorage.getItem(THEME_KEY);
    } catch (e) {
      saved = null;
    }
    if (saved) document.documentElement.setAttribute("data-theme", saved);

    function label() {
      var t = document.documentElement.getAttribute("data-theme") || "light";
      return t === "dark" ? "☾ dark" : "☀ light";
    }
    toggleBtn.textContent = label();
    toggleBtn.addEventListener("click", function () {
      var t = document.documentElement.getAttribute("data-theme") === "dark"
        ? "light"
        : "dark";
      document.documentElement.setAttribute("data-theme", t);
      try {
        localStorage.setItem(THEME_KEY, t);
      } catch (e) {
        /* non-fatal */
      }
      toggleBtn.textContent = label();
    });
  }

  function init() {
    var sidebarEl = document.getElementById("sidebar");
    var mainEl = document.getElementById("main");
    var themeBtn = document.getElementById("theme-toggle");
    var state = { active: null };

    var navButtons = buildSidebar(sidebarEl, mainEl, state);
    if (themeBtn) initTheme(themeBtn);

    var startId = "osx-surface";
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && VIEWS.some(function (v) { return v.id === saved; })) {
        startId = saved;
      }
    } catch (e) {
      /* non-fatal */
    }

    mountView(startId, mainEl, navButtons, state);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  OSX.router = { VIEWS: VIEWS };
})(window);
