"""Mashina tarjimasi (Google Translate ochiq endpointi) + kesh + Dota atamalarini himoyalash.

* Geroy, skill, predmet nomlari tarjima qilinmaydi (o'yinchilar inglizcha nomlarni ishlatadi).
* data/uz_glossary.json - tarjimadan keyingi tuzatishlar (masalan "hayratda qoldiradi" -> "stun qiladi").
* data/uz_overrides.json - aniq matn uchun qo'lda yozilgan tarjima (eng ustun).
"""
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

from common import CACHE, DATA, UA

_lock = threading.Lock()
_caches = {}

PROTECT_DEFAULT = [
    "Aghanim's Scepter", "Aghanim's Shard", "Aghanim's Blessing", "Aghanim", "Roshan", "Tormentor", "Aegis",
    "Radiant", "Dire", "Spell Immunity", "Spell Immune", "Debuff Immunity", "True Strike", "Break",
    "Lotus Orb", "Linken's Sphere", "Black King Bar", "BKB", "Wisdom Rune", "Bounty Rune", "Watcher",
    "Lotus Pool", "Twin Gate", "Outpost", "Shard", "Scepter", "Blink",
]


def _cache(tgt):
    if tgt not in _caches:
        p = os.path.join(CACHE, f"tr_{tgt}.json")
        _caches[tgt] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return _caches[tgt]


def save_cache():
    os.makedirs(CACHE, exist_ok=True)
    with _lock:
        for tgt, c in _caches.items():
            with open(os.path.join(CACHE, f"tr_{tgt}.json"), "w", encoding="utf-8") as f:
                json.dump(c, f, ensure_ascii=False)


def _load_json(name, default):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


_terms = []


def set_protected_terms(terms):
    global _terms
    seen = set()
    out = []
    for t in list(terms) + PROTECT_DEFAULT:
        t = (t or "").strip()
        if len(t) < 3 or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(t)
    out.sort(key=len, reverse=True)
    _terms = out


def _protect(text):
    slots = []

    def keep(s):
        slots.append(s)
        return f" X{len(slots) - 1}Q "

    # HTML teglar (translate_uz ularni oldindan olib tashlaydi; bu - ehtiyot uchun)
    text = re.sub(r"<[^>]+>", lambda m: keep(m.group(0)), text)
    if _terms:
        pat = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in _terms) + r")(?![A-Za-z])")
        text = pat.sub(lambda m: keep(m.group(0)), text)
    return text, slots


def _restore(text, slots):
    def back(m):
        i = int(m.group(1))
        return slots[i] if i < len(slots) else m.group(0)

    # Nomdan keyin ajralib qolgan o'zbekcha qo'shimchalarni yopishtiramiz: "Pudge ning" -> "Pudgening"
    suf = r"(?:\s+(ning|ni|ga|da|dan|dagi|lar|larni|larga|larning|dek|cha|day|dir)\b)?"
    text = re.sub(r"\s?X\s?(\d+)\s?Q" + suf + r"\s?",
                  lambda m: " " + back(m) + ("" if not m.group(2) else ("'" if back(m)[-1:].isdigit() else "") + m.group(2)) + " ",
                  text)
    text = re.sub(r"\s+([.,;:!?)%])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s*(<br>)\s*", r"\1", text)
    text = re.sub(r"(<b>|<strong[^>]*>)\s+", r"\1", text)
    text = re.sub(r"\s+(</b>|</strong>)", r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _postfix(text, tgt):
    if tgt != "uz":
        return text
    for a, b in _load_json("uz_glossary.json", []):
        text = re.sub(a, b, text)
    return text


def _call(q, src, tgt):
    url = ("https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl=%s&tl=%s&q=%s"
           % (src, tgt, urllib.parse.quote(q)))
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            return "".join(seg[0] for seg in d[0] if seg and seg[0])
        except Exception:
            time.sleep(2 + 4 * i)
    return None


SEP = "\n\n"


def _final(src, raw, tgt):
    _, slots = _protect(src.replace("\n", " "))
    return _postfix(_restore(raw, slots), tgt)


def translate_many(texts, tgt, src="auto", max_chars=3500):
    """Matnlar ro'yxatini tarjima qiladi; natija - shu tartibda."""
    cache = _cache(tgt)
    overrides = _load_json(f"{tgt}_overrides.json", {}) if tgt == "uz" else {}
    out = [None] * len(texts)
    todo = []
    for i, t in enumerate(texts):
        if not t or not re.search(r"[A-Za-zА-Яа-я]", t):
            out[i] = t
        elif t in overrides:
            out[i] = overrides[t]
        elif t in cache:
            out[i] = _final(t, cache[t], tgt)
        else:
            todo.append(i)
    # Takrorlarni bir marta tarjima qilamiz
    uniq = []
    seen = set()
    for i in todo:
        if texts[i] not in seen:
            seen.add(texts[i])
            uniq.append(texts[i])

    batch, size = [], 0

    def flush(batch):
        if not batch:
            return
        prot = [_protect(t.replace("\n", " ")) for t in batch]
        joined = SEP.join(p[0] for p in prot)
        res = _call(joined, src, tgt)
        parts = res.split(SEP) if res else []
        if len(parts) != len(batch):
            parts = []
            for p in prot:  # bittadan
                r = _call(p[0], src, tgt)
                parts.append(r if r is not None else None)
        with _lock:
            for t, (pt, slots), r in zip(batch, prot, parts):
                if r is not None:
                    cache[t] = r.strip()  # xom tarjima (X0Q belgilari bilan) saqlanadi

    for t in uniq:
        L = len(t) + 2
        if batch and size + L > max_chars:
            flush(batch)
            batch, size = [], 0
        batch.append(t)
        size += L
    flush(batch)
    for i in todo:
        t = texts[i]
        out[i] = _final(t, cache[t], tgt) if t in cache else t
    return out
