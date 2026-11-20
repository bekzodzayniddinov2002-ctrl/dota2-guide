"""Dota 2 ma'lumotlarini yig'adi (eng so'nggi patch, hozir 7.42).

Manbalar:
  * Valve datafeed (dota2.com/datafeed) - geroylar, skillar, Aghanim/Shard, predmetlar, patch notelari (en/ru)
  * OpenDota API - buildlar (itemPopularity) va 7.42 dagi o'yinlar statistikasi (explorer SQL)

Ishga tushirish:  python tools/build_data.py            (hammasi)
                  python tools/build_data.py --no-stats (statistikasiz, tezroq)
"""
import argparse
import datetime as dt
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (cached_json, fetch_json, save, load, fill_placeholders, clean_html,
                    join_vals, fmt_num, stat_label)

VALVE = "https://www.dota2.com/datafeed"
OD = "https://api.opendota.com/api"
LANGS = {"en": "english", "ru": "russian"}
ROLES = ["carry", "support", "nuker", "disabler", "jungler", "durable", "escape", "pusher", "initiator"]
ATTRS = ["str", "agi", "int", "all"]


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- patch
def latest_patch():
    pl = fetch_json(f"{VALVE}/patchnoteslist?language=english")
    patches = pl.get("patches") or pl.get("result", {}).get("patches") or []
    # Asosiy patch (harfsiz) — eng oxirgi
    majors = [p for p in patches if re.fullmatch(r"\d+\.\d+", p["patch_number"])]
    letters = [p for p in patches if p["patch_number"].startswith(majors[-1]["patch_number"])]
    return majors[-1], letters[-1]


# ---------------------------------------------------------------- heroes
def short_hero(name):
    return name.replace("npc_dota_hero_", "")


def talent_text(t, bonus_by_talent):
    name = t.get("name_loc") or ""
    vals = bonus_by_talent.get(t["name"], [])
    own = {sv["name"]: sv for sv in t.get("special_values", [])}

    def rep(m):
        key = m.group(1)
        if key in own and own[key].get("values_float"):
            return join_vals(own[key]["values_float"])
        if vals:
            return fmt_num(vals.pop(0)) if len(vals) > 0 else "?"
        num = re.findall(r"(\d+(?:\.\d+)?)$", t["name"])
        return num[0] if num else "?"

    name = re.sub(r"\{s:([a-zA-Z0-9_]+)\}", rep, name)
    return clean_html(name)


def build_hero(hid, lang_code):
    raw = cached_json(f"hero_{hid}_{lang_code}",
                      f"{VALVE}/herodata?language={LANGS[lang_code]}&hero_id={hid}")
    return raw["result"]["data"]["heroes"][0]


def hero_record(hid):
    per = {lc: build_hero(hid, lc) for lc in LANGS}
    h = per["en"]
    rec = {
        "id": h["id"], "key": short_hero(h["name"]), "name": h["name_loc"],
        "attr": ATTRS[h["primary_attr"]] if h["primary_attr"] < 4 else "all",
        "complexity": h["complexity"],
        "attack": "melee" if h["attack_capability"] == 1 else "ranged",
        "roles": {ROLES[i]: lv for i, lv in enumerate(h["role_levels"]) if lv > 0},
        "stats": {k: h[k] for k in ("str_base", "str_gain", "agi_base", "agi_gain", "int_base", "int_gain",
                                     "damage_min", "damage_max", "attack_rate", "attack_range",
                                     "projectile_speed", "armor", "magic_resistance", "movement_speed",
                                     "turn_rate", "sight_range_day", "sight_range_night", "max_health",
                                     "health_regen", "max_mana", "mana_regen")},
        "abilities": [], "talents": [], "text": {},
    }
    # Skillar (til-mustaqil qism)
    shown = []
    for a in h["abilities"]:
        if a["name"].endswith("_empty") or a["name"].startswith("generic_hidden"):
            continue
        shown.append(a["name"])
        rec["abilities"].append({
            "id": a["id"], "key": a["name"],
            "innate": a.get("ability_is_innate", False),
            "has_scepter": a.get("ability_has_scepter", False),
            "has_shard": a.get("ability_has_shard", False),
            "by_scepter": a.get("ability_is_granted_by_scepter", False),
            "by_shard": a.get("ability_is_granted_by_shard", False),
            "cooldown": join_vals(a.get("cooldowns") or []),
            "mana": join_vals(a.get("mana_costs") or []),
            "cast_range": join_vals(a.get("cast_ranges") or []),
            "max_level": a.get("max_level", 0),
            "dispellable": a.get("dispellable", 0), "immunity": a.get("immunity", 0),
            "damage_type": a.get("damage", 0),
            "values": [{"name": sv["name"], "v": join_vals(sv.get("values_float") or [], sv.get("is_percentage")),
                        "scepter": join_vals(sv.get("values_scepter") or [], sv.get("is_percentage")),
                        "shard": join_vals(sv.get("values_shard") or [], sv.get("is_percentage"))}
                       for sv in a.get("special_values", []) if sv.get("heading_loc")],
        })
    # Talantlar: 8 ta, juft-juft 10/15/20/25-darajalar (o'ng = juft indeks)
    levels = [10, 10, 15, 15, 20, 20, 25, 25]
    for i, t in enumerate(h["talents"]):
        rec["talents"].append({"key": t["name"], "level": levels[i] if i < 8 else 25, "side": "right" if i % 2 == 0 else "left"})

    for lc, hd in per.items():
        bonus_by_talent = {}
        for a in hd["abilities"]:
            for sv in a.get("special_values", []):
                for b in sv.get("bonuses", []):
                    bonus_by_talent.setdefault(b["name"], []).append(b["value"])
        amap = {a["name"]: a for a in hd["abilities"]}
        allsv = {}
        for a in hd["abilities"]:
            for sv in a.get("special_values", []):
                allsv.setdefault(sv["name"].lower(), sv)
        txt = {
            "name": hd["name_loc"],
            "hype": clean_html(hd.get("hype_loc")),
            "short": clean_html(hd.get("npe_desc_loc")),
            "abilities": {}, "talents": {},
        }
        for name in shown:
            a = amap[name]
            labels = {sv["name"]: stat_label(sv["heading_loc"].rstrip(":").strip(), lc)
                      for sv in a.get("special_values", []) if sv.get("heading_loc")}
            txt["abilities"][name] = {
                "name": a["name_loc"],
                "desc": clean_html(fill_placeholders(a.get("desc_loc"), a, None, allsv)),
                "notes": [clean_html(fill_placeholders(n, a)) for n in a.get("notes_loc", []) if n],
                "scepter": clean_html(fill_placeholders(a.get("scepter_loc"), a, "scepter", allsv)),
                "shard": clean_html(fill_placeholders(a.get("shard_loc"), a, "shard", allsv)),
                "lore": clean_html(a.get("lore_loc")),
                "labels": labels,
            }
        for t in hd["talents"]:
            txt["talents"][t["name"]] = talent_text(t, {k: list(v) for k, v in bonus_by_talent.items()})
        rec["text"][lc] = txt
    return rec


# ---------------------------------------------------------------- items
def item_short(name):
    return name.replace("item_", "")


def build_items():
    lists = {lc: cached_json(f"itemlist_{lc}", f"{VALVE}/itemlist?language={ln}")["result"]["data"]["itemabilities"]
             for lc, ln in LANGS.items()}
    base = lists["en"]
    by_id = {it["id"]: it for it in base}
    recipes = {}  # natija item nomi -> komponent id lar
    for it in base:
        if it["name"].startswith("item_recipe_") and it["recipes"]:
            target = "item_" + it["name"][len("item_recipe_"):]
            comps = [c for c in it["recipes"][0]["items"]]
            recipes[target] = {"components": comps, "recipe_id": it["id"]}
    wanted = [it for it in base if not it["name"].startswith("item_recipe_")]

    def get(it_lc):
        it, lc = it_lc
        try:
            d = cached_json(f"item_{it['id']}_{lc}", f"{VALVE}/itemdata?language={LANGS[lc]}&item_id={it['id']}")
            return (it["id"], lc, d["result"]["data"]["items"][0])
        except Exception as e:  # noqa
            return (it["id"], lc, None)

    jobs = [(it, lc) for it in wanted for lc in LANGS]
    details = {}
    with ThreadPoolExecutor(8) as ex:
        for i, (iid, lc, d) in enumerate(ex.map(get, jobs)):
            if d:
                details[(iid, lc)] = d
            if i % 200 == 0:
                log(f"  predmetlar: {i}/{len(jobs)}")

    name_to_id = {it["name"]: it["id"] for it in base}
    meta, texts = [], {lc: {} for lc in LANGS}
    builds_into = {}
    for it in wanted:
        d = details.get((it["id"], "en"))
        if not d:
            continue
        neutral = it["neutral_item_tier"] if it["neutral_item_tier"] >= 0 else None
        cost = d.get("item_cost", 0)
        rec = recipes.get(it["name"])
        comps = []
        recipe_cost = 0
        if rec:
            for cid in rec["components"]:
                if cid in by_id and not by_id[cid]["name"].startswith("item_recipe_"):
                    comps.append(cid)
            rdet = None
            try:
                rdet = cached_json(f"item_{rec['recipe_id']}_en",
                                   f"{VALVE}/itemdata?language=english&item_id={rec['recipe_id']}")["result"]["data"]["items"][0]
            except Exception:
                pass
            recipe_cost = rdet.get("item_cost", 0) if rdet else 0
            for c in comps:
                builds_into.setdefault(c, []).append(it["id"])
        if neutral is not None:
            cat = "neutral"
        elif comps:
            cat = "upgrade"
        elif cost == 0:
            cat = "special"
        else:
            cat = "basic"
        meta.append({
            "id": it["id"], "key": item_short(it["name"]), "cost": cost, "cat": cat, "tier": neutral,
            "components": comps, "recipe_cost": recipe_cost,
            "cooldown": join_vals(d.get("cooldowns") or []), "mana": join_vals(d.get("mana_costs") or []),
            "quality": d.get("item_quality"),
        })
        for lc in LANGS:
            dl = details.get((it["id"], lc)) or d
            texts[lc][it["id"]] = {
                "name": dl["name_loc"],
                "desc": clean_html(fill_placeholders(dl.get("desc_loc"), dl)),
                "notes": [clean_html(fill_placeholders(n, dl)) for n in dl.get("notes_loc", []) if n],
                "lore": clean_html(dl.get("lore_loc")),
                "values": [{"label": stat_label(sv["heading_loc"].rstrip(":"), lc), "v": join_vals(sv.get("values_float") or [], sv.get("is_percentage"))}
                           for sv in dl.get("special_values", []) if sv.get("heading_loc")],
            }
    for m in meta:
        m["builds_into"] = builds_into.get(m["id"], [])
    # Ko'rinmaydigan / eski predmetlarni tozalash: nom yo'q yoki "dota_tooltip" bo'lsa
    good = [m for m in meta if texts["en"][m["id"]]["name"] and not texts["en"][m["id"]]["name"].startswith("DOTA_")]
    return good, texts, name_to_id


# ---------------------------------------------------------------- patch notes
def build_patch(version):
    out = {}
    for lc, ln in LANGS.items():
        p = fetch_json(f"{VALVE}/patchnotes?version={version}&language={ln}")

        def notes(lst):
            res = []
            for n in lst or []:
                txt = clean_html(n.get("note", ""))
                if not txt or txt == "<br>":
                    continue
                res.append({"t": txt, "i": n.get("indent_level", 1), "info": clean_html(n.get("info", ""))})
            return res

        gen = [{"title": g.get("title", ""), "notes": notes(g.get("generic"))} for g in p.get("general_notes", [])]
        items = []
        for sec_key in ("items", "neutral_items"):
            for it in p.get(sec_key, []) or []:
                items.append({"id": it.get("ability_id"), "title": it.get("title", ""),
                              "general": it.get("is_general_note", False),
                              "notes": notes(it.get("ability_notes") or it.get("notes") or []),
                              "neutral": sec_key == "neutral_items"})
        heroes = []
        for h in p.get("heroes", []) or []:
            heroes.append({
                "id": h["hero_id"],
                "notes": notes(h.get("hero_notes")),
                "abilities": [{"id": a.get("ability_id"), "notes": notes(a.get("ability_notes"))}
                              for a in h.get("abilities", []) or []],
                "talents": notes(h.get("talent_notes")),
                "facets": [{"notes": notes(f.get("ability_notes") or f.get("notes"))} for f in h.get("subsections", []) or []],
            })
        creeps = [{"title": c.get("title", ""), "notes": notes(c.get("ability_notes") or c.get("notes"))}
                  for c in p.get("neutral_creeps", []) or []]
        out[lc] = {"version": version, "general": gen, "items": items, "heroes": heroes, "creeps": creeps}
    return out


# ---------------------------------------------------------------- stats (7.42 o'yinlari)
STAT_SQL = """
WITH m AS (SELECT radiant_win, radiant_team, dire_team FROM public_matches
           WHERE match_id > {a} AND match_id <= {b} AND start_time >= {ts} AND lobby_type = 7),
s AS (SELECT radiant_win AS win, radiant_team AS t, dire_team AS e FROM m
      UNION ALL SELECT NOT radiant_win, dire_team, radiant_team FROM m),
p AS (SELECT 'a' AS k, x.h AS h, y.h AS o, win FROM s, unnest(t) x(h), unnest(t) y(h) WHERE x.h <> y.h
      UNION ALL
      SELECT 'e', x.h, y.h, win FROM s, unnest(t) x(h), unnest(e) y(h))
SELECT k, h, o, count(*) g, sum(win::int) w FROM p GROUP BY k, h, o
"""


def explorer(sql):
    return fetch_json(f"{OD}/explorer?sql=" + urllib.parse.quote(sql), retries=2, timeout=90, pause=1.1)


def first_match_id(ts):
    # match_id ~ vaqt bo'yicha o'sadi: PK indeksi bo'yicha ikkilik qidiruv (tez)
    def st(x):
        r = explorer(f"SELECT match_id, start_time FROM public_matches WHERE match_id >= {x} ORDER BY match_id LIMIT 1")
        rows = r.get("rows", [])
        return (rows[0]["start_time"], rows[0]["match_id"]) if rows else (10**12, x)

    lo, hi = 8_000_000_000, 9_900_000_000
    while hi - lo > 20_000:
        mid = (lo + hi) // 2
        if st(mid)[0] < ts:
            lo = mid
        else:
            hi = mid
    return st(lo)[1]


def last_match_id(lo):
    """Bazadagi eng oxirgi o'yin match_id si (ikkilik qidiruv)."""
    def exists(x):
        return bool(explorer(f"SELECT match_id FROM public_matches WHERE match_id >= {x} ORDER BY match_id LIMIT 1").get("rows"))

    hi = lo + 50_000_000
    while hi - lo > 20_000:
        mid = (lo + hi) // 2
        if exists(mid):
            lo = mid
        else:
            hi = mid
    return hi


def build_stats(patch_ts, max_chunks=60, chunk=120_000):
    """Patch boshidan beri o'ynalgan o'yinlar; patch eskirsa — faqat eng oxirgi max_chunks bo'lak
    (taxminan 2 mln o'yin), shunda statistika hozirgi metani ko'rsatadi."""
    start = first_match_id(patch_ts)
    end = last_match_id(start)
    log(f"  patch birinchi o'yini: {start}, oxirgisi: ~{end}")
    agg = {}
    b = end
    n = 0
    while n < max_chunks and b > start:
        a = max(b - chunk, start - 1)
        try:
            r = explorer(STAT_SQL.format(a=a, b=b, ts=patch_ts))
        except RuntimeError as e:
            if chunk > 30_000:
                chunk //= 2
                log(f"  timeout, chunk -> {chunk}")
                continue
            log("  explorer xatosi:", e)
            break
        rows = r.get("rows", [])
        for row in rows:
            key = (row["k"], row["h"], row["o"])
            g, w = agg.get(key, (0, 0))
            agg[key] = (g + int(row["g"]), w + int(row["w"]))
        n += 1
        b = a
        if n % 5 == 0:
            log(f"  statistika bo'lagi {n}, match_id > {a}, juftliklar: {len(agg)}")
    # Geroy umumiy
    hero = {}
    for (k, h, o), (g, w) in agg.items():
        if k == "a":
            G, W = hero.get(h, (0, 0))
            hero[h] = (G + g, W + w)
    hero = {h: (g / 4, w / 4) for h, (g, w) in hero.items()}
    total_games = sum(g for g, _ in hero.values()) / 10
    return agg, hero, total_games


def analyse(agg, hero, total):
    res = {}
    wr = {h: (w / g if g else 0.5) for h, (g, w) in hero.items()}
    for hid, (g, w) in hero.items():
        res[hid] = {"games": int(g), "wr": round(w / g, 4) if g else 0, "pick": round(g / total, 4) if total else 0,
                    "allies": [], "vs": []}
    min_g = max(30, int(total * 0.0015))
    for (k, h, o), (g, w) in agg.items():
        if h not in res or o not in wr or g < min_g:
            continue
        actual = w / g
        if k == "a":
            adv = actual - (wr[h] + wr[o] - 0.5)
            res[h]["allies"].append({"id": o, "g": g, "wr": round(actual, 4), "adv": round(adv, 4)})
        else:
            adv = actual - (wr[h] - wr[o] + 0.5)
            res[h]["vs"].append({"id": o, "g": g, "wr": round(actual, 4), "adv": round(adv, 4)})
    for h, r in res.items():
        r["allies"].sort(key=lambda x: -x["adv"])
        vs = sorted(r["vs"], key=lambda x: -x["adv"])
        r["good_vs"] = vs[:10]
        r["bad_vs"] = list(reversed(vs[-10:]))
        r["best_allies"] = r["allies"][:10]
        r["worst_allies"] = list(reversed(r["allies"][-5:]))
        del r["vs"], r["allies"]
    return res


def build_item_popularity(hero_ids, item_ok):
    out = {}

    def one(hid):
        try:
            d = cached_json(f"itempop_{hid}", f"{OD}/heroes/{hid}/itemPopularity", pause=1.1)
        except Exception:
            return hid, None
        phases = {}
        for ph in ("start_game_items", "early_game_items", "mid_game_items", "late_game_items"):
            items = [(int(k), v) for k, v in (d.get(ph) or {}).items() if int(k) in item_ok]
            items.sort(key=lambda x: -x[1])
            phases[ph.split("_")[0]] = items[:10]
        return hid, phases

    with ThreadPoolExecutor(1) as ex:  # OpenDota: ~60 so'rov/daqiqa
        for i, (hid, ph) in enumerate(ex.map(one, hero_ids)):
            if ph:
                out[hid] = ph
            if i % 20 == 0:
                log(f"  buildlar: {i}/{len(hero_ids)}")
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-stats", action="store_true")
    ap.add_argument("--chunks", type=int, default=60)
    ap.add_argument("--fresh", action="store_true", help="Valve/OpenDota keshini tozalab, hammasini qayta yuklash")
    args = ap.parse_args()
    if args.fresh:
        import glob as _g
        from common import CACHE
        for pat in ("hero_*", "item_*", "itemlist_*", "itempop_*"):
            for p in _g.glob(os.path.join(CACHE, pat)):
                os.remove(p)

    major, last = latest_patch()
    version = major["patch_number"]
    log(f"Patch: {version} (oxirgisi: {last['patch_number']})")

    hl = fetch_json(f"{VALVE}/herolist?language=english")["result"]["data"]["heroes"]
    ids = sorted(h["id"] for h in hl)
    log(f"Geroylar: {len(ids)}")

    def hr(hid):
        return hero_record(hid)

    heroes = []
    with ThreadPoolExecutor(6) as ex:
        for i, rec in enumerate(ex.map(hr, ids)):
            heroes.append(rec)
            if i % 25 == 0:
                log(f"  geroylar: {i}/{len(ids)}")

    log("Predmetlar...")
    items, item_texts, _ = build_items()
    item_ok = {m["id"] for m in items if m["cat"] != "neutral"}
    log(f"  {len(items)} ta predmet")

    log("Patch notelari...")
    patch = build_patch(version)

    log("Buildlar (OpenDota)...")
    builds = build_item_popularity(ids, item_ok)

    stats = {}
    total = 0
    if not args.no_stats:
        log("7.42 statistikasi (OpenDota explorer)...")
        agg, hero_tot, total = build_stats(major["patch_timestamp"], max_chunks=args.chunks)
        stats = analyse(agg, hero_tot, total)
        save("stats_raw_meta.json", {"total": total})
    else:
        old = load("heroes.json")
        if old:
            stats = {h["id"]: {"games": h.get("games", 0), "wr": h.get("wr", 0), "pick": h.get("pick", 0)} for h in old}

    # Saqlash
    index = []
    for rec in heroes:
        st = stats.get(rec["id"], {})
        rec["builds"] = builds.get(rec["id"], {})
        for k in ("games", "wr", "pick", "good_vs", "bad_vs", "best_allies", "worst_allies"):
            if k in st:
                rec[k] = st[k]
        prev = load(f"heroes/{rec['id']}.json") or {}
        if "uz" in prev.get("text", {}):  # oldingi o'zbekcha tarjimani saqlab qolamiz
            rec["text"]["uz"] = prev["text"]["uz"]
        if args.no_stats:
            for k in ("good_vs", "bad_vs", "best_allies", "worst_allies"):
                if k in prev:
                    rec[k] = prev[k]
        save(f"heroes/{rec['id']}.json", rec)
        index.append({"id": rec["id"], "key": rec["key"], "name": rec["name"], "attr": rec["attr"],
                      "attack": rec["attack"], "complexity": rec["complexity"], "roles": rec["roles"],
                      "names": {lc: rec["text"][lc]["name"] for lc in rec["text"]},
                      "games": st.get("games", 0), "wr": st.get("wr", 0), "pick": st.get("pick", 0)})
    index.sort(key=lambda h: h["name"])
    save("heroes.json", index)
    save("items.json", items)
    for lc, t in item_texts.items():
        save(f"items.{lc}.json", t)
    for lc, p in patch.items():
        save(f"patch.{lc}.json", p)
    prev_meta = load("meta.json") or {}
    save("meta.json", {
        "patch": version, "patch_letter": last["patch_number"], "patch_date": major["patch_timestamp"],
        "built_at": int(time.time()),
        "stats_games": int(total) if total else prev_meta.get("stats_games", 0),
    })
    log("Tayyor.")


if __name__ == "__main__":
    main()
