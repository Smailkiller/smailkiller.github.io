/* Трактирная книга — фильтры, поиск, свечи и прочая магия. Без библиотек. */
(function () {
  "use strict";

  var norm = function (s) { return String(s || "").toLowerCase().replace(/ё/g, "е"); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var MULTI = { tags: " ", flavors: "|" };

  function plural(n, one, few, many) {
    var m = Math.abs(n) % 100, d = m % 10;
    if (m > 10 && m < 20) return many;
    return d === 1 ? one : d >= 2 && d <= 4 ? few : many;
  }

  function store(kind) {
    try { var s = window[kind]; s.setItem("__t", "1"); s.removeItem("__t"); return s; } catch (e) { return null; }
  }

  /* ───────── фильтры каталогов и лент ───────── */
  $$(".filterbox").forEach(function (box) {
    var list = document.querySelector(box.getAttribute("data-target"));
    if (!list) return;
    var items = $$(":scope > *", list);
    var section = box.closest("section") || document;
    var nothing = section.querySelector(".nothing");
    var moreBtn = section.querySelector("[data-more]");
    var counter = document.querySelector('[data-count-for="' + list.id + '"]');
    var pageSize = parseInt(box.getAttribute("data-page"), 10) || 0;
    var limit = pageSize;
    var searchInput = box.querySelector("[data-search]");
    var sortSelect = box.querySelector("[data-sort]");

    function values(el, facet) {
      var raw = el.getAttribute("data-" + facet) || "";
      return MULTI[facet] ? raw.split(MULTI[facet]).filter(Boolean) : [raw];
    }

    function apply(resetLimit) {
      if (resetLimit) limit = pageSize;
      var words = norm(searchInput ? searchInput.value : "").split(/\s+/).filter(Boolean);
      var groups = $$(".chips[data-group]", box).map(function (g) {
        return {
          facet: g.getAttribute("data-group"),
          mode: g.getAttribute("data-mode") || "any",
          on: $$(".chip.is-on", g).map(function (c) { return c.getAttribute("data-value"); })
        };
      }).filter(function (g) { return g.on.length; });
      var bounds = $$("[data-max],[data-min]", box).map(function (c) {
        var isMax = c.hasAttribute("data-max");
        var active = c.type === "checkbox" ? c.checked : c.value !== "";
        return active ? { attr: c.getAttribute(isMax ? "data-max" : "data-min"), max: isMax, v: parseFloat(c.value) } : null;
      }).filter(Boolean);

      var matched = items.filter(function (el) {
        var hay = norm(el.getAttribute("data-search"));
        for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) < 0) return false;
        for (var g = 0; g < groups.length; g++) {
          var vals = values(el, groups[g].facet);
          var hit = groups[g].mode === "all"
            ? groups[g].on.every(function (v) { return vals.indexOf(v) >= 0; })
            : groups[g].on.some(function (v) { return vals.indexOf(v) >= 0; });
          if (!hit) return false;
        }
        for (var b = 0; b < bounds.length; b++) {
          var x = parseFloat(el.getAttribute("data-" + bounds[b].attr));
          if (isNaN(x) || (bounds[b].max ? x > bounds[b].v : x < bounds[b].v)) return false;
        }
        return true;
      });

      if (sortSelect) {
        var parts = sortSelect.value.split("-"), field = parts[0], dir = parts[1] === "asc" ? 1 : -1;
        var sorted = items.slice().sort(function (a, b) {
          var va = a.getAttribute("data-" + field) || "", vb = b.getAttribute("data-" + field) || "";
          var na = parseFloat(va), nb = parseFloat(vb);
          var c = (!isNaN(na) && !isNaN(nb) && field !== "date") ? na - nb : va.localeCompare(vb, "ru");
          if (c === 0 && field !== "date") c = (a.getAttribute("data-date") || "").localeCompare(b.getAttribute("data-date") || "") * -dir;
          return c * dir;
        });
        sorted.forEach(function (el) { list.appendChild(el); });
        matched.sort(function (a, b) { return sorted.indexOf(a) - sorted.indexOf(b); });
      }

      var shown = 0;
      items.forEach(function (el) { el.hidden = true; });
      matched.forEach(function (el) {
        if (!limit || shown < limit) { el.hidden = false; shown++; }
      });
      if (nothing) nothing.hidden = matched.length > 0;
      if (moreBtn) moreBtn.hidden = !limit || matched.length <= limit;
      if (counter) counter.textContent = matched.length === items.length ? String(items.length) : matched.length + " из " + items.length;
    }

    box.addEventListener("click", function (e) {
      var chip = e.target.closest(".chip[data-value]");
      if (chip) { chip.classList.toggle("is-on"); chip.setAttribute("aria-pressed", chip.classList.contains("is-on")); apply(true); }
      if (e.target.closest("[data-reset]")) {
        $$(".chip.is-on", box).forEach(function (c) { c.classList.remove("is-on"); c.setAttribute("aria-pressed", "false"); });
        $$("input", box).forEach(function (i) { if (i.type === "checkbox") i.checked = false; else i.value = ""; });
        $$("select[data-max],select[data-min]", box).forEach(function (s) { s.value = ""; });
        if (sortSelect) sortSelect.selectedIndex = 0;
        apply(true);
      }
    });
    box.addEventListener("input", function () { apply(true); });
    box.addEventListener("change", function () { apply(true); });
    if (moreBtn) moreBtn.addEventListener("click", function () { limit += pageSize; apply(false); });
    $$(".chip[data-value]", box).forEach(function (c) { c.setAttribute("aria-pressed", "false"); });

    box._select = function (facet, value) {
      $$('.chips[data-group="' + facet + '"] .chip', box).forEach(function (c) {
        var on = c.getAttribute("data-value") === value;
        c.classList.toggle("is-on", on);
        c.setAttribute("aria-pressed", on);
      });
      apply(true);
    };
    apply(true);
  });

  /* быстрые ярлыки в келье ИИ: метка включает фильтр ленты */
  $$("[data-quicktag]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      var box = document.querySelector("#feed .filterbox");
      if (!box || !box._select) return;
      e.preventDefault();
      box._select("tags", a.getAttribute("data-quicktag"));
      document.getElementById("feed").scrollIntoView({ behavior: "smooth" });
    });
  });

  /* ───────── писарь: поиск по всем свиткам ───────── */
  var app = document.getElementById("search-app");
  if (app && window.TAVERN_INDEX) {
    var idx = window.TAVERN_INDEX, rooms = window.TAVERN_ROOMS || {};
    var q = document.getElementById("q"), roomSel = document.getElementById("room");
    var out = document.getElementById("results"), rc = document.getElementById("rc");
    var chips = $$("#tagchips .chip");
    var params = new URLSearchParams(location.search);
    var tags = params.getAll("tag").map(norm);
    var limit = 40;
    q.value = params.get("q") || "";
    roomSel.value = params.get("room") || "";

    var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    function mark(text, words) {
      var h = esc(text);
      words.forEach(function (w) {
        if (w.length < 2) return;
        var re = new RegExp("(" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/е/g, "[её]") + ")", "gi");
        h = h.replace(re, "<mark>$1</mark>");
      });
      return h;
    }
    function ruDate(d) {
      var m = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
      var p = d.split("-");
      return +p[2] + " " + m[+p[1] - 1] + " " + p[0];
    }

    function run(more) {
      if (!more) limit = 40;
      var words = norm(q.value).split(/\s+/).filter(Boolean);
      var room = roomSel.value;
      var res = [];
      idx.forEach(function (p) {
        if (room && p.r.indexOf(room) < 0) return;
        for (var i = 0; i < tags.length; i++) if (p.h.indexOf(tags[i]) < 0) return;
        var s = norm(p.s), t = norm(p.t), score = 0;
        for (var j = 0; j < words.length; j++) {
          if (s.indexOf(words[j]) < 0) return;
          score += (t.indexOf(words[j]) >= 0 ? 3 : 1) + (p.h.indexOf(words[j].replace(/^#/, "")) >= 0 ? 2 : 0);
        }
        res.push({ p: p, score: score });
      });
      res.sort(function (a, b) { return b.score - a.score || (a.p.d < b.p.d ? 1 : -1); });
      chips.forEach(function (c) { c.classList.toggle("is-on", tags.indexOf(c.getAttribute("data-tag")) >= 0); });
      var what = words.length || tags.length || room ? "Найдено" : "Всего в картотеке";
      rc.textContent = what + ": " + res.length + " " + plural(res.length, "свиток", "свитка", "свитков") +
        (tags.length ? " · метки: #" + tags.join(", #") : "");
      out.innerHTML = res.slice(0, limit).map(function (r) {
        var p = r.p;
        var letter = (p.t.match(/[0-9A-Za-zА-Яа-яЁё]/) || ["Ѣ"])[0].toUpperCase();
        var thumb = p.i ? '<img src="' + esc(p.i) + '" alt="" loading="lazy">'
          : '<div class="initial" style="--h:' + ((p.id * 47) % 360) + '"><span>' + esc(letter) + "</span></div>";
        var roomName = p.r.length ? rooms[p.r[0]] : "без комнаты";
        return '<li><a class="thumb" href="scroll/' + p.id + '.html" tabindex="-1" aria-hidden="true">' + thumb + "</a><div>" +
          '<h3><a href="scroll/' + p.id + '.html">' + mark(p.t, words) + "</a></h3>" +
          '<p class="meta">' + ruDate(p.d) + " · " + esc(roomName) + "</p>" +
          "<p>" + mark(p.x, words) + "</p></div></li>";
      }).join("") + (res.length > limit ? '<li class="more-row" style="display:block;text-align:center;box-shadow:none;border:0;background:none"><button type="button" class="btn" id="more-res">Ещё свитков</button></li>' : "");
      if (!res.length) out.innerHTML = '<li style="display:block">Писарь перерыл сундуки и ничего не нашёл. Попробуй другое слово.</li>';
      var mb = document.getElementById("more-res");
      if (mb) mb.addEventListener("click", function () { limit += 40; run(true); });
      var u = new URLSearchParams();
      if (q.value) u.set("q", q.value);
      if (room) u.set("room", room);
      tags.forEach(function (t) { u.append("tag", t); });
      try { history.replaceState(null, "", location.pathname + (u.toString() ? "?" + u : "")); } catch (e) { /* file:// */ }
    }
    q.addEventListener("input", function () { run(false); });
    roomSel.addEventListener("change", function () { run(false); });
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        var t = c.getAttribute("data-tag"), i = tags.indexOf(t);
        if (i >= 0) tags.splice(i, 1); else tags.push(t);
        run(false);
      });
    });
    run(false);
    if (!q.value && !tags.length) q.focus();
  }

  /* ───────── свечной счётчик ───────── */
  var cRow = document.querySelector(".candle-row"), cText = document.querySelector(".candle-text");
  if (cRow && cText) {
    var ls = store("localStorage"), ss = store("sessionStorage"), n = 1;
    if (ls) {
      n = parseInt(ls.getItem("tavern-visits") || "0", 10) || 0;
      if (!ss || !ss.getItem("tavern-here")) { n += 1; ls.setItem("tavern-visits", String(n)); if (ss) ss.setItem("tavern-here", "1"); }
      n = Math.max(n, 1);
    }
    cRow.innerHTML = new Array(Math.min(n, 24) + 1).join("<i></i>");
    cText.textContent = n === 1 ? "Ты здесь впервые, путник. Зажжена одна свеча."
      : "Ты заходил " + n + " " + plural(n, "раз", "раза", "раз") + ". Горит " + n + " " + plural(n, "свеча", "свечи", "свечей") + (n > 24 ? " (на полке место кончилось)." : ".");
  }

  /* цитаты в подвале */
  var qEl = document.querySelector("[data-quotes]");
  if (qEl) {
    try {
      var qs = JSON.parse(qEl.getAttribute("data-quotes"));
      qEl.textContent = qs[Math.floor(Math.random() * qs.length)];
    } catch (e) { /* пусть будет первая */ }
  }

  /* лайтбокс */
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a.zoom");
    if (!a) return;
    e.preventDefault();
    var lb = document.createElement("div");
    lb.className = "lightbox";
    lb.setAttribute("role", "dialog");
    lb.setAttribute("aria-label", "Картинка, нажми чтобы закрыть");
    lb.innerHTML = '<img src="' + a.getAttribute("href") + '" alt="">';
    var close = function () { lb.remove(); document.removeEventListener("keydown", onKey); };
    var onKey = function (ev) { if (ev.key === "Escape") close(); };
    lb.addEventListener("click", close);
    document.addEventListener("keydown", onKey);
    document.body.appendChild(lb);
  });

  /* спойлеры на тач-экранах */
  $$(".spoiler").forEach(function (s) { s.addEventListener("click", function () { s.classList.toggle("is-open"); }); });

  /* ───────── общий зал ───────── */
  if (document.body.classList.contains("is-hall")) {
    var root = document.documentElement;
    window.addEventListener("pointermove", function (e) {
      root.style.setProperty("--mx", e.clientX + "px");
      root.style.setProperty("--my", e.clientY + "px");
    }, { passive: true });

    var frame = document.querySelector(".scene-frame");
    if (frame && frame.scrollWidth > frame.clientWidth) frame.scrollLeft = (frame.scrollWidth - frame.clientWidth) / 2;

    /* пасхалка: улитка побеждает рыцаря */
    var snail = document.querySelector(".pix-snail"), hits = 0;
    if (snail) {
      var lines = ["Улитка наступает.", "Рыцарь дрогнул.", "Улитка неумолима.", "Рыцарь молится.", "Ещё немного…", "Рыцарь пишет завещание."];
      snail.addEventListener("click", function () {
        hits++;
        var hint = document.querySelector(".scene-hint");
        if (!hint) return;
        hint.textContent = hits >= 7 ? "Улитка победила рыцаря. Как и предсказано в рукописях XIII века."
          : lines[(hits - 1) % lines.length];
      });
    }
  }
})();
