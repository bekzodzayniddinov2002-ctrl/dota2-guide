"""Steam yangiliklari: yuklash, tozalash, uz/ru/en ga tarjima.

    python tools/news.py      -> data/news.uz.json, data/news.ru.json, data/news.en.json
"""
import html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import save  # noqa: E402
import translator  # noqa: E402

NEWS_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=570&count=40&maxlength=0&format=json"
LANGS = ("uz", "ru", "en")


def _plain(text, limit=420):
    text = text or ""
    text = re.sub(r"\[img\].*?\[/img\]", " ", text, flags=re.S | re.I)
    text = re.sub(r"\[/?[a-z0-9*]+(=[^\]]*)?\]", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\{STEAM_CLAN_IMAGE\}\S*", " ", text)
    text = html.unescape(re.sub(r"https?://\S+", " ", text))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def _image(text):
    m = re.search(r"\{STEAM_CLAN_IMAGE\}([^\s\[\]\"<]+)", text or "")
    if m:
        return "https://clan.akamai.steamstatic.com/images/" + m.group(1)
    m = re.search(r"(https?://[^\s\[\]\"<>]+\.(?:png|jpe?g|webp|gif))", text or "", re.I)
    return m.group(1) if m else None


def fetch_raw():
    req = urllib.request.Request(NEWS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    items = []
    for n in d.get("appnews", {}).get("newsitems", []):
        raw = n.get("contents", "")
        title = html.unescape(n.get("title", ""))
        lang = "ru" if re.search(r"[А-Яа-яЁё]", title + raw[:200]) else "en"
        items.append({
            "id": n["gid"], "title": title, "summary": _plain(raw), "lang": lang,
            "url": n.get("url"), "date": n.get("date"), "source": n.get("feedlabel") or "Steam",
            "official": n.get("feedname") == "steam_community_announcements",
            "image": _image(raw),
        })
    return items


def localize(items, lang):
    need = [i for i, it in enumerate(items) if it["lang"] != lang]
    src = [t for i in need for t in (items[i]["title"], items[i]["summary"])]
    tr = translator.translate_many(src, lang) if src else []
    translator.save_cache()
    out, k = [], 0
    for i, it in enumerate(items):
        it2 = dict(it)
        if i in need:
            it2["title"], it2["summary"] = tr[k], tr[k + 1]
            it2["translated"] = True
            it2["orig_title"] = it["title"]
            k += 2
        out.append(it2)
    return out


def main():
    items = fetch_raw()
    for lang in LANGS:
        save(f"news.{lang}.json", {"items": localize(items, lang)})
    print(f"Yangiliklar: {len(items)} ta, {', '.join(LANGS)}", flush=True)


if __name__ == "__main__":
    main()
