/* URANO OSX — Publication Bridge view.
 * Resolves DOI metadata/open-access locations through the local bridge and
 * exposes explicit analysis handoffs for connected research tools.
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function safeLink(url, label) {
    var a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = label;
    return a;
  }

  function renderResult(target, data) {
    target.innerHTML = "";
    if (!data || !data.ok) {
      var fail = el("div", "panel");
      fail.appendChild(el("h2", null, "Resolution HOLD"));
      fail.appendChild(el("p", "view-lede", (data && (data.error || data.access_state)) || "Unresolved"));
      target.appendChild(fail);
      return;
    }

    var meta = data.metadata || {};
    var panel = el("div", "panel");
    panel.appendChild(el("h2", null, "Resolved publication"));
    panel.appendChild(el("div", "mono", data.doi || ""));
    panel.appendChild(el("h3", null, meta.title || "Title unavailable"));
    var detail = [meta.journal, meta.publisher].filter(Boolean).join(" · ");
    if (detail) panel.appendChild(el("p", "view-lede", detail));
    panel.appendChild(el("span", "pill " + (meta.is_open_access ? "state-ok" : "state-hold"), data.access_state));
    panel.appendChild(document.createTextNode(" "));
    panel.appendChild(safeLink(data.canonical_url, "DOI"));
    target.appendChild(panel);

    var locations = Array.isArray(data.access_locations) ? data.access_locations : [];
    var access = el("div", "panel");
    access.appendChild(el("h2", null, "Legal access locations"));
    if (!locations.length) {
      access.appendChild(el("p", "view-lede", "No verified open-access location was returned. Use institutional/user-authorized access; no bypass is attempted."));
    } else {
      var ul = document.createElement("ul");
      locations.forEach(function (item) {
        var li = document.createElement("li");
        li.appendChild(safeLink(item.url, (item.source || "OA") + " · " + (item.kind || "link")));
        if (item.version) li.appendChild(document.createTextNode(" · " + item.version));
        if (item.license) li.appendChild(document.createTextNode(" · " + item.license));
        ul.appendChild(li);
      });
      access.appendChild(ul);
    }
    target.appendChild(access);

    var handoffs = el("div", "panel");
    handoffs.appendChild(el("h2", null, "Plugin / connector analysis handoffs"));
    var list = document.createElement("ul");
    (data.analysis_handoffs || []).forEach(function (item) {
      var li = document.createElement("li");
      var strong = document.createElement("strong");
      strong.textContent = item.id;
      li.appendChild(strong);
      li.appendChild(document.createTextNode(" · " + item.operation + " · query: " + item.query));
      if (item.note) li.appendChild(document.createTextNode(" — " + item.note));
      list.appendChild(li);
    });
    handoffs.appendChild(list);
    target.appendChild(handoffs);

    var links = data.analysis_links || {};
    var linksPanel = el("div", "panel");
    linksPanel.appendChild(el("h2", null, "Analysis links"));
    var linksList = document.createElement("ul");
    Object.keys(links).forEach(function (key) {
      var li = document.createElement("li");
      li.appendChild(safeLink(links[key], key));
      linksList.appendChild(li);
    });
    linksPanel.appendChild(linksList);
    target.appendChild(linksPanel);
  }

  function mount(root) {
    root.innerHTML = "";
    root.appendChild(el("h1", "view-title", "Publication Bridge"));
    root.appendChild(el("p", "view-lede", "DOI-first resolution: Crossref/OpenAlex/optional Unpaywall → legal OA locations → analysis handoffs. Paywall, CAPTCHA and authentication are never bypassed."));

    var panel = el("div", "panel");
    panel.appendChild(el("h2", null, "Resolve publication"));
    var form = document.createElement("form");
    form.className = "cassandra-bar";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "DOI or URL containing DOI…";
    input.autocomplete = "off";
    var submit = el("button", "submit", "Resolve →");
    submit.type = "submit";
    form.appendChild(input);
    form.appendChild(submit);
    panel.appendChild(form);
    root.appendChild(panel);

    var result = document.createElement("div");
    root.appendChild(result);

    var base = global.location.origin.startsWith("http") ? global.location.origin : "http://localhost:8765";
    var controller = new AbortController();

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var value = input.value.trim();
      if (!value) return;
      submit.disabled = true;
      submit.textContent = "Resolving…";
      fetch(base + "/api/publication/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: value }),
        signal: controller.signal,
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          renderResult(result, data);
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            renderResult(result, { ok: false, error: "Publication bridge unreachable" });
          }
        })
        .finally(function () {
          submit.disabled = false;
          submit.textContent = "Resolve →";
        });
    });

    return {
      unmount: function () {
        controller.abort();
      },
    };
  }

  OSX.viewsPublications = { mount: mount };
})(window);
