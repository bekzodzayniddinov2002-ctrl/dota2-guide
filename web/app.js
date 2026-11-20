/* Dota 2 Qo'llanma — bitta sahifali ilova (framework-siz) */
(() => {
  const CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react";
  const IMG = {
    hero: (k) => `${CDN}/heroes/${k}.png`,
    ab: (k) => `${CDN}/abilities/${k}.png`,
    item: (k) => `${CDN}/items/${k}.png`,
    attr: (a) => `${CDN}/icons/hero_${{ str: "strength", agi: "agility", int: "intelligence", all: "universal" }[a]}.png`,
    scepter: `${CDN}/items/ultimate_scepter.png`,
    shard: `${CDN}/items/aghanims_shard.png`,
  };
  const $app = document.getElementById("app");
  const store = { lang: "uz", cache: {} };
  try { store.lang = localStorage.getItem("lang") || "uz"; } catch (e) {}
  if (!I18N[store.lang]) store.lang = "uz";

  // ---------------------------------------------------------------- helpers
  const T = (k, vars) => {
    let s = k.split(".").reduce((o, p) => (o ? o[p] : undefined), I18N[store.lang]);
    if (s === undefined) s = k.split(".").reduce((o, p) => (o ? o[p] : undefined), I18N.en) ?? k;
    if (vars) for (const [a, b] of Object.entries(vars)) s = s.replaceAll(`{${a}}`, b);
    return s;
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // Ma'lumotdagi HTML faqat <b>, <br>, <strong> teglaridan iborat (build_data.py tozalaydi)
  const safe = (s) => String(s ?? "").replace(/<(?!\/?(b|br|strong)( class='h')?\s*>)[^>]*>/g, "");
  const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
  const num = (n) => Number(n).toLocaleString(store.lang === "ru" ? "ru-RU" : "en-US");
  const sign = (x) => (x > 0 ? "+" : "") + (x * 100).toFixed(1) + "%";
  const nice = (s) => (s && s === s.toUpperCase() ? s.charAt(0) + s.slice(1).toLowerCase() : s || "");
  const imgErr = `onerror="this.style.visibility='hidden'"`;

  async function get(path) {
    if (store.cache[path]) return store.cache[path];
    const p = fetch(path).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
    store.cache[path] = p;
    try { return await p; } catch (e) { delete store.cache[path]; throw e; }
  }
  const data = {
    meta: () => get("data/meta.json"),
    heroes: () => get("data/heroes.json"),
    hero: (id) => get(`data/heroes/${id}.json`),
    items: () => get("data/items.json"),
    itemText: async () => { try { return await get(`data/items.${store.lang}.json`); } catch (e) { return get("data/items.en.json"); } },
    patch: async () => { try { return await get(`data/patch.${store.lang}.json`); } catch (e) { return get("data/patch.en.json"); } },
    news: () => get(`data/news.${store.lang}.json`).catch(() => get(`api/news?lang=${store.lang}`)),
  };
  const heroName = (h) => (h.names && (h.names[store.lang] || h.names.en)) || h.name;

  // ---------------------------------------------------------------- shell
  function shell() {
    document.documentElement.lang = store.lang;
    document.getElementById("brand-text").textContent = T("brand");
    document.querySelectorAll("[data-nav]").forEach((a) => (a.textContent = T("nav_" + a.dataset.nav)));
    document.querySelectorAll("#langs button").forEach((b) => b.classList.toggle("on", b.dataset.lang === store.lang));
    data.meta().then((m) => {
      document.getElementById("patch-chip").textContent = m.patch_letter || m.patch;
      const d = new Date(m.built_at * 1000).toLocaleDateString(store.lang === "ru" ? "ru-RU" : store.lang === "en" ? "en-GB" : "uz-UZ");
      document.getElementById("foot").innerHTML =
        `<p>${esc(T("data_note"))} ${esc(T("updated"))}: ${esc(d)}.</p>` +
        (T("mt_note") ? `<p>${esc(T("mt_note"))}</p>` : "") +
        `<p>Dota 2 — Valve Corporation. Bu norasmiy fan-sayt.</p>`;
    }).catch(() => {});
  }
  document.getElementById("langs").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-lang]");
    if (!b) return;
    store.lang = b.dataset.lang;
    try { localStorage.setItem("lang", store.lang); } catch (e) {}
    for (const k of Object.keys(store.cache)) if (/items\.|patch\.|news/.test(k)) delete store.cache[k];
    shell();
    route();
  });
  document.getElementById("menu-btn").addEventListener("click", () => document.getElementById("nav").classList.toggle("open"));

  // ---------------------------------------------------------------- router
  const routes = [
    [/^\/?$/, viewHome, "home"],
    [/^\/heroes$/, viewHeroes, "heroes"],
    [/^\/hero\/([a-z0-9_]+)(?:\/([a-z]+))?$/, viewHero, "heroes"],
    [/^\/items$/, viewItems, "items"],
    [/^\/item\/([a-z0-9_]+)$/, viewItem, "items"],
    [/^\/patch$/, viewPatch, "patch"],
    [/^\/news$/, viewNews, "news"],
  ];
  let routeToken = 0;
  async function route() {
    const path = decodeURIComponent(location.hash.replace(/^#/, "").split("?")[0]) || "/";
    const tok = ++routeToken;
    document.getElementById("nav").classList.remove("open");
    for (const [re, fn, nav] of routes) {
      const m = path.match(re);
      if (m) {
        document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === nav));
        $app.innerHTML = `<div class="loading">${esc(T("loading"))}</div>`;
        try {
          const html = await fn(...m.slice(1));
          if (tok !== routeToken) return;
          if (typeof html === "string") $app.innerHTML = html;
          if (fn.after) fn.after(...m.slice(1));
        } catch (e) {
          console.error(e);
          if (tok === routeToken) $app.innerHTML = `<div class="empty">${esc(T("not_found"))}</div>`;
        }
        return;
      }
    }
    $app.innerHTML = `<div class="empty">${esc(T("not_found"))}</div>`;
  }
  window.addEventListener("hashchange", () => { route(); window.scrollTo(0, 0); });

  // ---------------------------------------------------------------- pieces
  const heroLink = (h, right = "") =>
    `<a class="li" href="#/hero/${h.key}"><img class="hp" src="${IMG.hero(h.key)}" alt="" loading="lazy" ${imgErr}><div class="grow"><div class="nm">${esc(heroName(h))}</div></div>${right}</a>`;

  function newsCards(items) {
    return items.map((n) => {
      const d = new Date(n.date * 1000).toLocaleDateString(store.lang === "ru" ? "ru-RU" : "en-GB");
      return `<article class="ncard">
        ${n.image ? `<img src="${esc(n.image)}" alt="" loading="lazy" ${imgErr}>` : ""}
        <div class="b">
          <div class="src">${n.official ? `<span class="pill innate">${esc(T("news_official"))}</span>` : ""}<span>${esc(n.source)}</span><span>· ${esc(d)}</span>${n.translated ? `<span title="${esc(n.orig_title || "")}">· ${esc(T("news_translated"))}</span>` : ""}</div>
          <h3>${esc(n.title)}</h3>
          <p>${esc(n.summary)}</p>
          <a class="more" href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">${esc(T("read_more"))} ↗</a>
        </div></article>`;
    }).join("");
  }

  // ---------------------------------------------------------------- HOME
  async function viewHome() {
    const [meta, heroes, patch] = await Promise.all([data.meta(), data.heroes(), data.patch().catch(() => null)]);
    const withStats = heroes.filter((h) => h.games > 0);
    const minG = Math.max(50, (meta.stats_games || 0) * 0.01);
    const topWr = withStats.filter((h) => h.games >= minG).sort((a, b) => b.wr - a.wr).slice(0, 10);
    const topPick = [...withStats].sort((a, b) => b.pick - a.pick).slice(0, 10);
    const date = new Date(meta.patch_date * 1000).toLocaleDateString(store.lang === "ru" ? "ru-RU" : "en-GB");
    const maxWr = Math.max(...topWr.map((h) => h.wr), 0.55);
    const maxPick = Math.max(...topPick.map((h) => h.pick), 0.01);
    const highlights = patch ? patch.general.slice(0, 2).map((g) => `
      <div class="card"><h3>${esc(g.title)}</h3><ul class="pnotes">${g.notes.filter((n) => n.i === 1 && !/^<b>/.test(n.t)).slice(0, 6).map((n) => `<li>${safe(n.t)}</li>`).join("")}</ul></div>`).join("") : "";
    const html = `
      <section class="banner">
        <div class="row"><div class="big">${esc(meta.patch_letter || meta.patch)}</div>
          <div><h1>${esc(T("patch_banner", { v: meta.patch }))}</h1>
          <div class="muted">${esc(T("patch_released"))}: ${esc(date)}</div></div></div>
        <div class="stats">
          <div><b>${heroes.length}</b><span class="muted small">${esc(T("nav_heroes"))}</span></div>
          ${meta.stats_games ? `<div><b>${num(meta.stats_games)}</b><span class="muted small">${esc(T("games_analyzed", { n: "" }).trim())}</span></div>` : ""}
        </div>
      </section>
      ${withStats.length ? `<div class="grid2" style="margin-top:20px">
        <div class="card"><div class="sec-head" style="margin-top:0"><h2>${esc(T("home_top_wr"))}</h2><a href="#/heroes?sort=wr">${esc(T("see_all"))}</a></div>
          <div class="list">${topWr.map((h) => heroLink(h, `<div class="num good" style="width:70px">${pct(h.wr)}<div class="bar good"><i style="width:${(h.wr / maxWr) * 100}%"></i></div></div>`)).join("")}</div></div>
        <div class="card"><div class="sec-head" style="margin-top:0"><h2>${esc(T("home_top_pick"))}</h2><a href="#/heroes?sort=pick">${esc(T("see_all"))}</a></div>
          <div class="list">${topPick.map((h) => heroLink(h, `<div class="num" style="width:70px">${pct(h.pick)}<div class="bar"><i style="width:${(h.pick / maxPick) * 100}%"></i></div></div>`)).join("")}</div></div>
      </div>` : ""}
      ${highlights ? `<div class="sec-head"><h2>${esc(T("home_patch"))}</h2><a href="#/patch">${esc(T("see_all"))}</a></div><div class="grid2">${highlights}</div>` : ""}
      <div class="sec-head"><h2>${esc(T("home_news"))}</h2><a href="#/news">${esc(T("see_all"))}</a></div>
      <div class="news" id="home-news"><div class="loading">${esc(T("loading"))}</div></div>`;
    return html;
  }
  viewHome.after = () => {
    const tok = routeToken;
    data.news().then((r) => {
      if (tok !== routeToken) return;
      const el = document.getElementById("home-news");
      if (el) el.innerHTML = newsCards((r.items || []).slice(0, 6)) || `<div class="empty">${esc(T("news_error"))}</div>`;
    }).catch(() => {
      const el = document.getElementById("home-news");
      if (el) el.innerHTML = `<div class="empty">${esc(T("news_error"))}</div>`;
    });
  };

  // ---------------------------------------------------------------- HEROES
  const hf = { q: "", attr: "", attack: "", role: "", sort: "name" };
  async function viewHeroes() {
    const qs = new URLSearchParams(location.hash.split("?")[1] || "");
    if (qs.get("sort")) hf.sort = qs.get("sort");
    await data.heroes();
    const attrBtn = (a) => `<button data-attr="${a}" class="${hf.attr === a ? "on" : ""}">${a ? `<img class="attr-ico" src="${IMG.attr(a)}" alt="">` : ""}${esc(a ? T(a === "all" ? "all_attr" : a) : T("all"))}</button>`;
    return `
      <h1>${esc(T("nav_heroes"))}</h1>
      <div class="controls">
        <input class="input search" id="hq" placeholder="${esc(T("search_hero"))}" value="${esc(hf.q)}">
        <div class="seg" id="hattr">${["", "str", "agi", "int", "all"].map(attrBtn).join("")}</div>
      </div>
      <div class="controls">
        <select class="input" id="hrole"><option value="">${esc(T("role"))}: ${esc(T("all"))}</option>${Object.entries(T("roles")).map(([k, v]) => `<option value="${k}" ${hf.role === k ? "selected" : ""}>${esc(v)}</option>`).join("")}</select>
        <select class="input" id="hatk"><option value="">${esc(T("attack"))}: ${esc(T("all"))}</option><option value="melee" ${hf.attack === "melee" ? "selected" : ""}>${esc(T("melee"))}</option><option value="ranged" ${hf.attack === "ranged" ? "selected" : ""}>${esc(T("ranged"))}</option></select>
        <select class="input" id="hsort">${["name", "wr", "pick"].map((s) => `<option value="${s}" ${hf.sort === s ? "selected" : ""}>${esc(T("sort"))}: ${esc(T("sort_" + s))}</option>`).join("")}</select>
      </div>
      <div class="hgrid" id="hgrid"></div>`;
  }
  viewHeroes.after = async () => {
    const heroes = await data.heroes();
    const grid = document.getElementById("hgrid");
    const draw = () => {
      const q = hf.q.trim().toLowerCase();
      let list = heroes.filter((h) =>
        (!hf.attr || h.attr === hf.attr) && (!hf.attack || h.attack === hf.attack) && (!hf.role || h.roles[hf.role]) &&
        (!q || Object.values(h.names || {}).some((n) => n.toLowerCase().includes(q)) || h.key.includes(q)));
      if (hf.sort === "wr") list.sort((a, b) => b.wr - a.wr);
      else if (hf.sort === "pick") list.sort((a, b) => b.pick - a.pick);
      else list.sort((a, b) => heroName(a).localeCompare(heroName(b)));
      grid.innerHTML = list.map((h) => `
        <a class="hcard" href="#/hero/${h.key}" title="${esc(heroName(h))}">
          <img src="${IMG.hero(h.key)}" alt="" loading="lazy" ${imgErr}>
          ${h.games ? `<span class="wr ${h.wr >= 0.5 ? "good" : "bad"}">${pct(h.wr)}</span>` : ""}
          <div class="nm"><span class="dot ${h.attr}"></span>${esc(heroName(h))}</div>
        </a>`).join("") || `<div class="empty">${esc(T("not_found"))}</div>`;
    };
    document.getElementById("hq").addEventListener("input", (e) => { hf.q = e.target.value; draw(); });
    document.getElementById("hattr").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      hf.attr = b.dataset.attr;
      document.querySelectorAll("#hattr button").forEach((x) => x.classList.toggle("on", x === b));
      draw();
    });
    document.getElementById("hrole").addEventListener("change", (e) => { hf.role = e.target.value; draw(); });
    document.getElementById("hatk").addEventListener("change", (e) => { hf.attack = e.target.value; draw(); });
    document.getElementById("hsort").addEventListener("change", (e) => { hf.sort = e.target.value; draw(); });
    draw();
  };

  // ---------------------------------------------------------------- HERO
  const TABS = ["abilities", "aghs", "builds", "matchups", "talents", "stats", "patch"];
  async function viewHero(key, tab) {
    tab = TABS.includes(tab) ? tab : "abilities";
    const heroes = await data.heroes();
    const meta = heroes.find((h) => h.key === key);
    if (!meta) throw new Error("hero");
    const [h, items, itext, patch, gmeta] = await Promise.all([data.hero(meta.id), data.items(), data.itemText(), data.patch().catch(() => null), data.meta()]);
    const tx = h.text[store.lang] || h.text.en;
    const name = tx.name;
    const byId = Object.fromEntries(heroes.map((x) => [x.id, x]));
    const itemById = Object.fromEntries(items.map((x) => [x.id, x]));
    const ctx = { h, tx, name, byId, itemById, itext, patch, gmeta, heroes };

    const st = h.stats;
    const attrs = [["str", st.str_base, st.str_gain], ["agi", st.agi_base, st.agi_gain], ["int", st.int_base, st.int_gain]];
    const roles = Object.entries(h.roles).sort((a, b) => b[1] - a[1]).map(([r]) => `<span class="pill">${esc(T("roles." + r))}</span>`).join("");
    const head = `
      <a class="back" href="#/heroes">${esc(T("back"))}</a>
      <section class="hero-head">
        <img class="portrait" src="${IMG.hero(h.key)}" alt="${esc(name)}" ${imgErr}>
        <div>
          <div class="row"><img class="attr-ico" style="width:26px;height:26px" src="${IMG.attr(h.attr)}" alt=""><h1>${esc(name)}</h1></div>
          <div class="wrap-row" style="margin-top:6px"><span class="pill">${esc(T(h.attack))}</span>${roles}<span class="pill">${esc(T("complexity"))}: ${"◆".repeat(h.complexity)}${"◇".repeat(3 - h.complexity)}</span></div>
          <p class="hype">${safe(tx.hype)}</p>
          <div class="attrs">${attrs.map(([a, b, g]) => `<div class="${h.attr === a ? "prim" : ""}"><img class="attr-ico" src="${IMG.attr(a)}" alt="">${Math.round(b)} <span class="muted small">+${g}</span></div>`).join("")}</div>
          <div class="kpis">
            ${h.games ? `<div class="kpi"><span>${esc(T("winrate"))}</span><b class="${h.wr >= 0.5 ? "good" : "bad"}">${pct(h.wr)}</b></div>
            <div class="kpi"><span>${esc(T("pickrate"))}</span><b>${pct(h.pick)}</b></div>
            <div class="kpi"><span>${esc(T("games"))} (7.42)</span><b>${num(h.games)}</b></div>` : ""}
          </div>
        </div>
      </section>
      <div class="tabs" id="tabs">${TABS.map((t) => `<button data-tab="${t}" class="${t === tab ? "on" : ""}">${esc(T("tab_" + t))}</button>`).join("")}</div>
      <div id="tabc">${renderHeroTab(tab, ctx)}</div>`;
    viewHero._ctx = ctx;
    return head;
  }
  viewHero.after = (key) => {
    document.getElementById("tabs").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-tab]"); if (!b) return;
      history.replaceState(null, "", `#/hero/${key}/${b.dataset.tab}`);
      document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("on", x === b));
      document.getElementById("tabc").innerHTML = renderHeroTab(b.dataset.tab, viewHero._ctx);
    });
  };

  function renderHeroTab(tab, c) {
    switch (tab) {
      case "abilities": return tabAbilities(c);
      case "aghs": return tabAghs(c);
      case "builds": return tabBuilds(c);
      case "matchups": return tabMatchups(c);
      case "talents": return tabTalents(c);
      case "stats": return tabStats(c);
      case "patch": return tabHeroPatch(c);
    }
    return "";
  }

  function abilityValues(a, at) {
    if (!a.values.length) return "";
    return `<div class="vals">${a.values.map((v) => {
      const label = (at.labels && at.labels[v.name]) || v.name;
      const up = [v.scepter && `<span class="up" title="Scepter">⟶ ${esc(v.scepter)}</span>`, v.shard && `<span class="up" style="color:var(--shard)" title="Shard">⟶ ${esc(v.shard)}</span>`].filter(Boolean).join(" ");
      return `<div><span>${esc(nice(label))}</span><b>${esc(v.v)} ${up}</b></div>`;
    }).join("")}</div>`;
  }

  function tabAbilities(c) {
    const { h, tx } = c;
    return h.abilities.map((a) => {
      const at = tx.abilities[a.key] || {};
      const tags = [
        a.innate && `<span class="pill innate">${esc(T("innate"))}</span>`,
        a.by_scepter && `<span class="pill scepter">${esc(T("granted_scepter"))}</span>`,
        a.by_shard && `<span class="pill shard">${esc(T("granted_shard"))}</span>`,
      ].filter(Boolean).join("");
      const metaRow = [
        a.cooldown && a.cooldown !== "0" && `<span>⏱ ${esc(T("cooldown"))}: <b>${esc(a.cooldown)}</b></span>`,
        a.mana && a.mana !== "0" && `<span>💧 ${esc(T("mana"))}: <b>${esc(a.mana)}</b></span>`,
        a.cast_range && a.cast_range !== "0" && `<span>🎯 ${esc(T("cast_range"))}: <b>${esc(a.cast_range)}</b></span>`,
      ].filter(Boolean).join("");
      const upg = [
        at.scepter && !a.by_scepter && `<div class="upg scepter"><img src="${IMG.scepter}" alt=""><div><div class="t">${esc(T("scepter_upgrade"))}</div>${safe(at.scepter)}</div></div>`,
        at.shard && !a.by_shard && `<div class="upg shard"><img src="${IMG.shard}" alt=""><div><div class="t">${esc(T("shard_upgrade"))}</div>${safe(at.shard)}</div></div>`,
      ].filter(Boolean).join("");
      return `<div class="ab">
        <img src="${IMG.ab(a.key)}" alt="" loading="lazy" ${imgErr}>
        <div>
          <div class="wrap-row"><h3>${esc(at.name || a.key)}</h3>${tags}</div>
          <div class="desc">${safe(at.desc)}</div>
          ${abilityValues(a, at)}
          ${metaRow ? `<div class="meta">${metaRow}</div>` : ""}
          ${upg}
          ${at.notes && at.notes.length ? `<details class="notes"><summary>${esc(T("notes"))} (${at.notes.length})</summary><ul>${at.notes.map((n) => `<li>${safe(n)}</li>`).join("")}</ul></details>` : ""}
          ${at.lore ? `<details class="notes"><summary>${esc(T("lore"))}</summary><p>${safe(at.lore)}</p></details>` : ""}
        </div></div>`;
    }).join("");
  }

  function tabAghs(c) {
    const { h, tx, name } = c;
    const col = (kind) => {
      const list = h.abilities.filter((a) => (kind === "scepter" ? a.has_scepter || a.by_scepter : a.has_shard || a.by_shard));
      const body = list.map((a) => {
        const at = tx.abilities[a.key] || {};
        const isNew = kind === "scepter" ? a.by_scepter : a.by_shard;
        const text = isNew ? at.desc : at[kind];
        return `<div class="aghs-item"><img src="${IMG.ab(a.key)}" alt="" loading="lazy" ${imgErr}><div>
          <div class="wrap-row"><b>${esc(at.name)}</b>${isNew ? `<span class="pill ${kind}">${esc(T("new_ability"))}</span>` : ""}</div>
          <div class="small" style="margin-top:4px">${safe(text || "")}</div></div></div>`;
      }).join("");
      return `<div class="aghs-col card"><h3><img src="${IMG[kind]}" alt="">Aghanim's ${kind === "scepter" ? "Scepter" : "Shard"}</h3>${body || `<div class="muted">${esc(T(kind === "scepter" ? "no_scepter" : "no_shard"))}</div>`}</div>`;
    };
    return `<p class="muted">${esc(T("aghs_intro", { hero: name }))}</p><div class="aghs-grid">${col("scepter")}${col("shard")}</div>`;
  }

  function tabBuilds(c) {
    const { h, itemById, itext } = c;
    const b = h.builds || {};
    const phases = ["start", "early", "mid", "late"];
    if (!phases.some((p) => (b[p] || []).length)) return `<div class="empty">${esc(T("no_stats"))}</div>`;
    return phases.map((p) => {
      const list = b[p] || [];
      if (!list.length) return "";
      const top = list[0][1] || 1;
      const total = Math.max(top, 1);
      return `<section class="phase card"><h3>${esc(T("phase_" + p))} <small>${esc(T("phase_" + p + "_hint"))}</small></h3>
        <div class="items-row">${list.map(([id, n]) => {
          const it = itemById[id]; if (!it) return "";
          const t = itext[id] || {};
          return `<div class="it"><a href="#/item/${it.key}"><img src="${IMG.item(it.key)}" alt="" loading="lazy" ${imgErr}><div class="n">${esc(t.name || it.key)}</div></a><div class="p">${Math.round((n / total) * 100)}%</div></div>`;
        }).join("")}</div></section>`;
    }).join("") + `<p class="note">${esc(T("builds_source"))}</p>`;
  }

  function mlist(list, byId, kind) {
    if (!list || !list.length) return `<div class="muted">${esc(T("no_stats"))}</div>`;
    const max = Math.max(...list.map((x) => Math.abs(x.adv)), 0.01);
    return `<div class="list">${list.map((x) => {
      const hh = byId[x.id]; if (!hh) return "";
      const cls = x.adv >= 0 ? "good" : "bad";
      return heroLink(hh, `<div class="num ${cls}" style="width:84px" title="${esc(T("winrate"))} ${pct(x.wr)} · ${esc(T("games"))} ${num(x.g)}">${sign(x.adv)}<div class="small muted" style="font-weight:400">${pct(x.wr)} · ${num(x.g)}</div><div class="bar ${cls}"><i style="width:${(Math.abs(x.adv) / max) * 100}%"></i></div></div>`);
    }).join("")}</div>`;
  }

  function tabMatchups(c) {
    const { h, byId, name, gmeta } = c;
    return `<div class="grid3">
      <div class="card"><h3>🤝 ${esc(T("best_allies"))}</h3><p class="small muted">${esc(T("best_allies_hint"))}</p>${mlist(h.best_allies, byId)}</div>
      <div class="card"><h3>⚔️ ${esc(T("good_vs"))}</h3><p class="small muted">${esc(T("good_vs_hint", { hero: name }))}</p>${mlist(h.good_vs, byId)}</div>
      <div class="card"><h3>🛡️ ${esc(T("bad_vs"))}</h3><p class="small muted">${esc(T("bad_vs_hint", { hero: name }))}</p>${mlist(h.bad_vs, byId)}</div>
    </div><p class="note">${esc(T("matchup_source", { n: num(gmeta.stats_games || 0) }))}</p>`;
  }

  function tabTalents(c) {
    const { h, tx } = c;
    const lv = {};
    h.talents.forEach((t, i) => { (lv[t.level] = lv[t.level] || [])[i % 2] = t; });
    const rows = [25, 20, 15, 10].map((l) => {
      const [r, lft] = lv[l] || [];
      return `<div class="trow"><div>${safe(lft ? tx.talents[lft.key] : "")}</div><div class="lv">${l}</div><div>${safe(r ? tx.talents[r.key] : "")}</div></div>`;
    }).join("");
    return `<p class="muted">${esc(T("talents_hint"))}</p><div class="talents">${rows}</div>`;
  }

  function tabStats(c) {
    const s = c.h.stats;
    const r = (k, v) => `<div><span>${esc(T(k))}</span><b>${v}</b></div>`;
    return `<div class="card"><h3>${esc(T("stats_base"))}</h3><div class="vals">
      ${r("health", Math.round(s.max_health))}${r("health_regen", (+s.health_regen).toFixed(1))}
      ${r("mana", Math.round(s.max_mana))}${r("mana_regen", (+s.mana_regen).toFixed(1))}
      ${r("damage", `${s.damage_min}–${s.damage_max}`)}${r("armor", (+s.armor).toFixed(1))}
      ${r("magic_res", s.magic_resistance + "%")}${r("move_speed", s.movement_speed)}
      ${r("attack_range", s.attack_range)}${r("attack_rate", s.attack_rate)}
      ${s.projectile_speed ? r("projectile", s.projectile_speed) : ""}${r("turn_rate", s.turn_rate)}
      ${r("vision", `${s.sight_range_day} / ${s.sight_range_night}`)}
      ${r("str", `${s.str_base} +${s.str_gain} ${T("gain")}`)}${r("agi", `${s.agi_base} +${s.agi_gain} ${T("gain")}`)}${r("int", `${s.int_base} +${s.int_gain} ${T("gain")}`)}
    </div></div>`;
  }

  function patchNotes(notes) {
    if (!notes || !notes.length) return "";
    return `<ul class="pnotes">${notes.map((n) => `<li class="i${Math.min(n.i || 1, 3)}">${safe(n.t)}${n.info ? `<span class="info">${safe(n.info)}</span>` : ""}</li>`).join("")}</ul>`;
  }

  function heroPatchBlock(ph, h, tx, withHead) {
    const abs = Object.fromEntries(h.abilities.map((a) => [a.id, a]));
    let html = "";
    if (ph.notes.length) html += patchNotes(ph.notes);
    for (const a of ph.abilities) {
      const ab = abs[a.id];
      const nm = ab ? (tx.abilities[ab.key] || {}).name : "";
      html += `<div class="pab">${ab ? `<img src="${IMG.ab(ab.key)}" alt="" loading="lazy" ${imgErr}>` : ""}${esc(nm || "")}</div>${patchNotes(a.notes)}`;
    }
    for (const f of ph.facets || []) html += patchNotes(f.notes);
    if (ph.talents.length) html += `<div class="pab">${esc(T("tab_talents"))}</div>${patchNotes(ph.talents)}`;
    if (!withHead) return html;
    return `<div class="card pblock" data-s="${esc((tx.name + " " + html.replace(/<[^>]+>/g, " ")).toLowerCase())}"><a class="ph" href="#/hero/${h.key}"><img class="hp" src="${IMG.hero(h.key)}" alt="" loading="lazy" ${imgErr}><h3 style="margin:0">${esc(tx.name)}</h3></a>${html}</div>`;
  }

  function tabHeroPatch(c) {
    const { h, tx, patch } = c;
    const ph = patch && patch.heroes.find((x) => x.id === h.id);
    if (!ph) return `<div class="empty">${esc(T("hero_patch_none"))}</div>`;
    return `<div class="card">${heroPatchBlock(ph, h, tx, false)}</div>`;
  }

  // ---------------------------------------------------------------- ITEMS
  const itf = { q: "", cat: "upgrade" };
  async function viewItems() {
    await Promise.all([data.items(), data.itemText()]);
    const cats = ["basic", "upgrade", "neutral", "special"];
    return `<h1>${esc(T("nav_items"))}</h1>
      <div class="controls"><input class="input search" id="iq" placeholder="${esc(T("search_item"))}" value="${esc(itf.q)}">
      <div class="seg" id="icat">${cats.map((c) => `<button data-cat="${c}" class="${itf.cat === c ? "on" : ""}">${esc(T("item_cat." + c))}</button>`).join("")}</div></div>
      <div id="igrid"></div>`;
  }
  viewItems.after = async () => {
    const [items, itext] = await Promise.all([data.items(), data.itemText()]);
    const el = document.getElementById("igrid");
    const draw = () => {
      const q = itf.q.trim().toLowerCase();
      let list = items.filter((i) => (q ? true : i.cat === itf.cat) && itext[i.id] && (!q || (itext[i.id].name || "").toLowerCase().includes(q) || i.key.includes(q)));
      const card = (i) => `<a class="icard" href="#/item/${i.key}"><img src="${IMG.item(i.key)}" alt="" loading="lazy" ${imgErr}><div class="n">${esc(itext[i.id].name)}</div>${i.cost ? `<div class="c">${num(i.cost)}</div>` : ""}</a>`;
      if (!q && itf.cat === "neutral") {
        const tiers = [...new Set(list.map((i) => i.tier))].sort((a, b) => a - b);
        el.innerHTML = tiers.map((t) => `<h2>${esc(T("tier"))} ${t + 1}</h2><div class="igrid">${list.filter((i) => i.tier === t).map(card).join("")}</div>`).join("");
      } else {
        list.sort((a, b) => a.cost - b.cost);
        el.innerHTML = `<div class="igrid">${list.map(card).join("")}</div>` + (list.length ? "" : `<div class="empty">${esc(T("not_found"))}</div>`);
      }
    };
    document.getElementById("iq").addEventListener("input", (e) => { itf.q = e.target.value; draw(); });
    document.getElementById("icat").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      itf.cat = b.dataset.cat;
      document.querySelectorAll("#icat button").forEach((x) => x.classList.toggle("on", x === b));
      draw();
    });
    draw();
  };

  async function viewItem(key) {
    const [items, itext, patch] = await Promise.all([data.items(), data.itemText(), data.patch().catch(() => null)]);
    const it = items.find((i) => i.key === key);
    if (!it) throw new Error("item");
    const t = itext[it.id] || {};
    const byId = Object.fromEntries(items.map((i) => [i.id, i]));
    const small = (id) => { const x = byId[id]; if (!x) return ""; return `<div class="it"><a href="#/item/${x.key}"><img src="${IMG.item(x.key)}" alt="" loading="lazy" ${imgErr}><div class="n">${esc((itext[id] || {}).name || x.key)}</div></a>${x.cost ? `<div class="p">${num(x.cost)}</div>` : ""}</div>`; };
    const pi = patch && patch.items.filter((p) => p.id === it.id);
    return `<a class="back" href="#/items">${esc(T("back"))}</a>
      <section class="item-head"><img src="${IMG.item(it.key)}" alt="" ${imgErr}><div>
        <h1>${esc(t.name)}</h1>
        <div class="wrap-row">${it.cost ? `<span class="cost">${num(it.cost)}</span>` : ""}<span class="pill">${esc(T("item_cat." + it.cat))}</span>${it.tier !== null && it.tier !== undefined ? `<span class="pill innate">${esc(T("tier"))} ${it.tier + 1}</span>` : ""}
        ${it.cooldown && it.cooldown !== "0" ? `<span class="pill">⏱ ${esc(it.cooldown)}</span>` : ""}${it.mana && it.mana !== "0" ? `<span class="pill">💧 ${esc(it.mana)}</span>` : ""}</div>
        ${t.lore ? `<p class="muted small"><i>${safe(t.lore)}</i></p>` : ""}
      </div></section>
      <div class="grid2" style="margin-top:18px">
        <div class="card"><div class="idesc">${safe(t.desc) || "—"}</div>
          ${t.values && t.values.length ? `<div class="vals" style="margin-top:12px">${t.values.map((v) => `<div><span>${esc(nice(v.label))}</span><b>${esc(v.v)}</b></div>`).join("")}</div>` : ""}
          ${t.notes && t.notes.length ? `<details class="notes" open><summary>${esc(T("notes"))}</summary><ul>${t.notes.map((n) => `<li>${safe(n)}</li>`).join("")}</ul></details>` : ""}
        </div>
        <div>
          ${it.components.length ? `<div class="card" style="margin-bottom:14px"><h3>${esc(T("components"))}</h3><div class="items-row">${it.components.map(small).join("")}${it.recipe_cost ? `<div class="it"><img src="${IMG.item("recipe")}" alt="" ${imgErr}><div class="n">${esc(T("recipe"))}</div><div class="p">${num(it.recipe_cost)}</div></div>` : ""}</div></div>` : ""}
          ${it.builds_into.length ? `<div class="card" style="margin-bottom:14px"><h3>${esc(T("builds_into"))}</h3><div class="items-row">${it.builds_into.map(small).join("")}</div></div>` : ""}
          ${pi && pi.length ? `<div class="card"><h3>${esc(T("item_patch"))}</h3>${pi.map((p) => patchNotes(p.notes)).join("")}</div>` : ""}
        </div>
      </div>`;
  }

  // ---------------------------------------------------------------- PATCH
  async function viewPatch() {
    const [patch, heroes, items, itext] = await Promise.all([data.patch(), data.heroes(), data.items(), data.itemText()]);
    const itemById = Object.fromEntries(items.map((i) => [i.id, i]));
    const heroById = Object.fromEntries(heroes.map((h) => [h.id, h]));
    const secs = [];
    secs.push(`<h2 id="p-general">${esc(T("patch_general"))}</h2>` + patch.general.map((g) =>
      `<div class="card pblock" data-s="${esc((g.title + " " + g.notes.map((n) => n.t).join(" ")).replace(/<[^>]+>/g, " ").toLowerCase())}"><h3>${esc(g.title)}</h3>${patchNotes(g.notes)}</div>`).join(""));
    secs.push(`<h2 id="p-items">${esc(T("patch_items"))}</h2>` + patch.items.map((p) => {
      const it = itemById[p.id];
      const nm = it ? (itext[p.id] || {}).name : p.title;
      if (!p.notes.length) return "";
      return `<div class="card pblock" data-s="${esc(((nm || "") + " " + p.notes.map((n) => n.t).join(" ")).replace(/<[^>]+>/g, " ").toLowerCase())}">
        <${it ? `a href="#/item/${it.key}"` : "div"} class="ph">${it ? `<img class="ip" src="${IMG.item(it.key)}" alt="" loading="lazy" ${imgErr}>` : ""}<h3 style="margin:0">${esc(nm || "")}</h3></${it ? "a" : "div"}>${patchNotes(p.notes)}</div>`;
    }).join(""));
    secs.push(`<h2 id="p-heroes">${esc(T("patch_heroes"))}</h2><div id="p-hero-list"><div class="loading">${esc(T("loading"))}</div></div>`);
    if (patch.creeps && patch.creeps.some((c) => c.notes.length)) secs.push(`<h2>${esc(T("patch_creeps"))}</h2>` + patch.creeps.map((c) => c.notes.length ? `<div class="card pblock"><h3>${esc(c.title)}</h3>${patchNotes(c.notes)}</div>` : "").join(""));
    viewPatch._ctx = { patch, heroById };
    return `<h1>Patch ${esc(patch.version)}</h1>
      <div class="controls"><input class="input search" id="pq" placeholder="${esc(T("search_patch"))}">
      <div class="seg"><button onclick="document.getElementById('p-general').scrollIntoView()">${esc(T("patch_general"))}</button><button onclick="document.getElementById('p-items').scrollIntoView()">${esc(T("patch_items"))}</button><button onclick="document.getElementById('p-heroes').scrollIntoView()">${esc(T("patch_heroes"))}</button></div></div>
      ${secs.join("")}`;
  }
  viewPatch.after = async () => {
    const { patch, heroById } = viewPatch._ctx;
    const tok = routeToken;
    // Geroylarning skill nomlari uchun har bir geroy faylini yuklaymiz (parallel, keshlanadi)
    const list = patch.heroes.filter((p) => heroById[p.id]);
    const full = await Promise.all(list.map((p) => data.hero(p.id).catch(() => null)));
    if (tok !== routeToken) return;
    const el = document.getElementById("p-hero-list");
    list.sort((a, b) => heroName(heroById[a.id]).localeCompare(heroName(heroById[b.id])));
    const fullById = Object.fromEntries(full.filter(Boolean).map((h) => [h.id, h]));
    el.innerHTML = list.map((p) => { const h = fullById[p.id]; if (!h) return ""; return heroPatchBlock(p, h, h.text[store.lang] || h.text.en, true); }).join("");
    const q = document.getElementById("pq");
    q.addEventListener("input", () => {
      const v = q.value.trim().toLowerCase();
      document.querySelectorAll(".pblock").forEach((b) => { b.style.display = !v || (b.dataset.s || "").includes(v) ? "" : "none"; });
    });
  };

  // ---------------------------------------------------------------- NEWS
  async function viewNews() {
    return `<h1>${esc(T("news_title"))}</h1><div class="news" id="news-list"><div class="loading">${esc(T("loading"))}</div></div>`;
  }
  viewNews.after = async () => {
    const tok = routeToken;
    try {
      const r = await data.news();
      if (tok !== routeToken) return;
      document.getElementById("news-list").innerHTML = newsCards(r.items || []) || `<div class="empty">${esc(T("news_error"))}</div>`;
    } catch (e) {
      document.getElementById("news-list").innerHTML = `<div class="empty">${esc(T("news_error"))}</div>`;
    }
  };

  shell();
  route();
})();
