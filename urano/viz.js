/* URANO OSX — viz.js
 * Shared rendering primitives: deterministic PRNG, Cube controller,
 * generative field (whirl) renderer, claim-graph renderer.
 * Clean-room reconstruction — see PROVENANCE.md
 */
(function (global) {
  "use strict";

  var OSX = (global.OSX = global.OSX || {});

  // ---- deterministic PRNG -------------------------------------------------

  function hashStr(s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = (h * 16777619) >>> 0;
    }
    return h >>> 0;
  }

  function mulberry32(seed) {
    var a = seed >>> 0;
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---- Cube controller -----------------------------------------------------
  // Six faces are identity-bearing: the labels change what the cube *means*,
  // never what it *is*. Rotation/morph are driven by the active SceneSpec.

  var FACE_ORDER = ["front", "right", "back", "left", "top", "bottom"];
  var FACE_LABELS = {
    front: "RESEARCH",
    right: "EVIDENCE",
    back: "EXPERIMENTS",
    left: "REPRO",
    top: "PUBLISH",
    bottom: "GOVERN",
  };
  var FACE_NORMALS = {
    front: { x: 0, y: 0, z: 1 },
    back: { x: 0, y: 0, z: -1 },
    right: { x: 1, y: 0, z: 0 },
    left: { x: -1, y: 0, z: 0 },
    top: { x: 0, y: 1, z: 0 },
    bottom: { x: 0, y: -1, z: 0 },
  };

  function rotateVec(v, rxDeg, ryDeg) {
    var ry = (ryDeg * Math.PI) / 180;
    var rx = (rxDeg * Math.PI) / 180;
    var x = v.x * Math.cos(ry) + v.z * Math.sin(ry);
    var y = v.y;
    var z = -v.x * Math.sin(ry) + v.z * Math.cos(ry);
    var y2 = y * Math.cos(rx) - z * Math.sin(rx);
    var z2 = y * Math.sin(rx) + z * Math.cos(rx);
    return { x: x, y: y2, z: z2 };
  }

  function createCubeController(rootEl) {
    var state = { rx: -18, ry: 28, morph: 0 };
    var faceEls = {};
    FACE_ORDER.forEach(function (id) {
      var el = document.createElement("div");
      el.className = "cube-face face-" + id;
      var span = document.createElement("span");
      span.textContent = FACE_LABELS[id];
      el.appendChild(span);
      rootEl.appendChild(el);
      faceEls[id] = { el: el, label: span };
    });

    function apply() {
      rootEl.style.setProperty("--rx", state.rx + "deg");
      rootEl.style.setProperty("--ry", state.ry + "deg");
      var radius = Math.round(state.morph * 40);
      var facing = null;
      var best = -2;
      FACE_ORDER.forEach(function (id) {
        var n = rotateVec(FACE_NORMALS[id], state.rx, state.ry);
        var facingAmount = Math.max(0, n.z);
        faceEls[id].el.style.borderRadius = radius + "%";
        faceEls[id].label.style.opacity = String(0.15 + facingAmount * 0.85);
        if (n.z > best) {
          best = n.z;
          facing = id;
        }
      });
      return facing;
    }

    return {
      setAngles: function (rx, ry) {
        state.rx = rx;
        state.ry = ry;
      },
      setMorph: function (m) {
        state.morph = Math.max(0, Math.min(1, m));
      },
      step: function (dtSeconds, motion) {
        state.ry += dtSeconds * (8 + motion * 46);
        state.rx = -18 + Math.sin(state.ry * 0.017) * (6 + motion * 10);
        return apply();
      },
      facingLabel: function () {
        var facing = apply();
        return facing ? FACE_LABELS[facing] : FACE_LABELS.front;
      },
      pulse: function () {
        rootEl.classList.remove("kernel-pulse");
        // eslint-disable-next-line no-unused-expressions
        rootEl.offsetWidth; // restart CSS animation
        rootEl.classList.add("kernel-pulse");
      },
    };
  }

  // ---- generative field (whirl) --------------------------------------------
  // Particle field whose vorticity/density/motion are read straight off the
  // active SceneSpec. This is decoration driven by state, not the state itself.

  function createFieldRenderer(canvas) {
    var ctx = canvas.getContext("2d");
    var particles = [];
    var w = 0,
      h = 0,
      dpr = Math.min(2, global.devicePixelRatio || 1);

    function resize() {
      var rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    global.addEventListener("resize", resize);

    function seedParticles(spec, count) {
      var rnd = mulberry32(spec.seed >>> 0 || 1);
      particles = [];
      for (var i = 0; i < count; i++) {
        var angle = rnd() * Math.PI * 2;
        var radius = (0.15 + rnd() * 0.4) * Math.min(w, h);
        particles.push({
          angle: angle,
          radius: radius,
          speed: 0.4 + rnd() * 0.9,
          wobble: rnd() * Math.PI * 2,
          r: 1 + rnd() * 2.2,
        });
      }
    }

    var lastSpecKey = "";

    function draw(spec, t) {
      var count = Math.round(24 + spec.density * 160);
      var key = spec.seed + ":" + count;
      if (key !== lastSpecKey) {
        seedParticles(spec, count);
        lastSpecKey = key;
      }

      var isDark =
        document.documentElement.getAttribute("data-theme") === "dark";
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = isDark
        ? "rgba(23,22,20,1)"
        : "rgba(244,242,238,1)";
      ctx.fillRect(0, 0, w, h);

      var cx = w / 2,
        cy = h / 2;
      var vortex = spec.whirl; // 0 = drift, 1 = tight inward spiral
      var motion = spec.motion;
      var dash = spec.epistemicClass === "SPECULATIVE_DREAM" ||
        spec.epistemicClass === "GENERATIVE_METAPHOR";

      ctx.strokeStyle = isDark
        ? "rgba(236,232,223,0.5)"
        : "rgba(28,27,25,0.45)";
      ctx.fillStyle = ctx.strokeStyle;
      ctx.lineWidth = 1;

      particles.forEach(function (p, i) {
        var localT = t * (0.06 + motion * 0.5) * p.speed;
        var spiralPull = spec.mode === "RITUAL" ? t * 0.02 : 0;
        var radius = Math.max(4, p.radius * (1 - vortex * 0.5) - spiralPull * 40);
        var angle =
          p.angle + localT + Math.sin(t * 0.3 + p.wobble) * vortex * 1.4;
        var x = cx + Math.cos(angle) * radius;
        var y = cy + Math.sin(angle) * radius * 0.62;

        if (dash) {
          ctx.beginPath();
          ctx.setLineDash([3, 4]);
          ctx.moveTo(cx, cy);
          ctx.lineTo(x, y);
          ctx.globalAlpha = 0.12;
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.globalAlpha = 1;
        }

        ctx.beginPath();
        ctx.arc(x, y, p.r, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    return {
      resize: resize,
      draw: draw,
      dims: function () {
        return { w: w, h: h };
      },
    };
  }

  // ---- claim dependency graph ------------------------------------------------

  function renderClaimGraph(svgEl, graph, tPulse) {
    while (svgEl.firstChild) svgEl.removeChild(svgEl.firstChild);
    var ns = "http://www.w3.org/2000/svg";
    var W = svgEl.viewBox && svgEl.viewBox.baseVal.width || 480;
    var H = svgEl.viewBox && svgEl.viewBox.baseVal.height || 260;

    var byId = {};
    graph.nodes.forEach(function (n) {
      byId[n.id] = n;
    });

    graph.edges.forEach(function (e) {
      var a = byId[e.from],
        b = byId[e.to];
      if (!a || !b) return;
      var path = document.createElementNS(ns, "line");
      path.setAttribute("x1", a.x * W);
      path.setAttribute("y1", a.y * H);
      path.setAttribute("x2", b.x * W);
      path.setAttribute("y2", b.y * H);
      path.setAttribute("class", "claim-edge");
      svgEl.appendChild(path);

      if (a.state === "CONTRADICTED" || a.state === "REVIEW_REQUIRED") {
        var progress = (tPulse * (0.4 + Math.random() * 0.1)) % 1;
        var px = a.x * W + (b.x * W - a.x * W) * progress;
        var py = a.y * H + (b.y * H - a.y * H) * progress;
        var pulse = document.createElementNS(ns, "circle");
        pulse.setAttribute("cx", px);
        pulse.setAttribute("cy", py);
        pulse.setAttribute("r", 2.6);
        pulse.setAttribute("class", "claim-pulse");
        svgEl.appendChild(pulse);
      }
    });

    graph.nodes.forEach(function (n) {
      var g = document.createElementNS(ns, "g");
      g.setAttribute(
        "class",
        "claim-node " +
          (n.state === "CONTRADICTED"
            ? "contradicted"
            : n.state === "REVIEW_REQUIRED"
            ? "review"
            : "supported")
      );
      var circle = document.createElementNS(ns, "circle");
      circle.setAttribute("cx", n.x * W);
      circle.setAttribute("cy", n.y * H);
      circle.setAttribute("r", 14);
      g.appendChild(circle);
      var text = document.createElementNS(ns, "text");
      text.setAttribute("x", n.x * W);
      text.setAttribute("y", n.y * H + 3);
      text.setAttribute("text-anchor", "middle");
      text.textContent = n.id;
      g.appendChild(text);
      svgEl.appendChild(g);
    });
  }

  OSX.viz = {
    hashStr: hashStr,
    mulberry32: mulberry32,
    createCubeController: createCubeController,
    createFieldRenderer: createFieldRenderer,
    renderClaimGraph: renderClaimGraph,
    FACE_LABELS: FACE_LABELS,
  };
})(window);
