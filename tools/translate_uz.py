"""Inglizcha ma'lumotlardan o'zbekcha (lotin) versiyasini yaratadi.

    python tools/translate_uz.py

Tarjimalar .cache/tr_uz.json da saqlanadi (qayta ishga tushirish tez).
Tuzatishlar:  data/uz_glossary.json  (regex, hamma joyga)
              data/uz_overrides.json (aniq inglizcha matn -> qo'lda yozilgan o'zbekcha)
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, load, save  # noqa: E402
import translator  # noqa: E402


def log(*a):
    print(*a, flush=True)


class Collector:
    """Matnlarni yig'ib, bitta katta to'plamda tarjima qiladi, keyin joyiga qo'yadi."""

    def __init__(self):
        self.texts = []
        self.setters = []

    def add(self, text, setter):
        """HTML'li matnni <br> bo'yicha bo'laklarga ajratadi; ichki <b> teglarini olib tashlaydi,
        to'liq o'ralgan sarlavhalarni (masalan <strong class='h'>Active: X</strong>) saqlaydi."""
        if not text:
            return
        if "<" not in text:
            self.texts.append(text)
            self.setters.append(setter)
            return
        parts = re.split(r"<br>", text)
        out = [""] * len(parts)
        wraps = []
        pending = {"n": 0}
        for i, p in enumerate(parts):
            m = re.fullmatch(r"\s*(<(b|strong)[^>]*>)([^<]*)(</\2>)\s*", p)
            if m:
                wraps.append((m.group(1), m.group(4)))
                core = m.group(3)
            else:
                wraps.append(("", ""))
                core = re.sub(r"<[^>]+>", "", p)
            if not core.strip():
                out[i] = wraps[i][0] + core + wraps[i][1]
                continue
            pending["n"] += 1

            def mk(i=i):
                def f(v):
                    out[i] = wraps[i][0] + v + wraps[i][1]
                    pending["n"] -= 1
                    if pending["n"] == 0:
                        setter("<br>".join(out))
                return f
            self.texts.append(core.strip())
            self.setters.append(mk())
        if pending["n"] == 0:
            setter("<br>".join(out))

    def run(self):
        log(f"  tarjima qilinadigan matnlar: {len(self.texts)}")
        step = 400
        for i in range(0, len(self.texts), step):
            part = self.texts[i:i + step]
            res = translator.translate_many(part, "uz", src="en")
            for s, r in zip(self.setters[i:i + step], res):
                s(r)
            translator.save_cache()
            log(f"  {min(i + step, len(self.texts))}/{len(self.texts)}")


def setter(obj, key):
    def f(v):
        obj[key] = v
    return f


def main():
    heroes = [load(os.path.relpath(p, DATA)) for p in sorted(glob.glob(os.path.join(DATA, "heroes", "*.json")))]
    items_en = load("items.en.json")
    patch_en = load("patch.en.json")

    terms = []
    for h in heroes:
        terms.append(h["text"]["en"]["name"])
        terms += [a["name"] for a in h["text"]["en"]["abilities"].values()]
    terms += [t["name"] for t in items_en.values()]
    translator.set_protected_terms(terms)

    c = Collector()
    for h in heroes:
        en = h["text"]["en"]
        uz = json.loads(json.dumps(en))
        uz["name"] = en["name"]
        c.add(en["hype"], setter(uz, "hype"))
        c.add(en["short"], setter(uz, "short"))
        for k, a in en["abilities"].items():
            ua = uz["abilities"][k]
            ua["name"] = a["name"]  # skill nomi inglizcha qoladi
            for f in ("desc", "scepter", "shard"):
                c.add(a[f], setter(ua, f))
            ua["lore"] = ""  # lore tarjima qilinmaydi (hajmi katta), inglizchasi ko'rsatiladi
            for i, n in enumerate(a["notes"]):
                c.add(n, setter(ua["notes"], i))
            for lk, lv in a["labels"].items():
                c.add(lv.title() if lv.isupper() else lv, setter(ua["labels"], lk))
        for k, t in en["talents"].items():
            c.add(t, setter(uz["talents"], k))
        h["text"]["uz"] = uz

    items_uz = json.loads(json.dumps(items_en))
    for iid, t in items_en.items():
        u = items_uz[iid]
        c.add(t["desc"], setter(u, "desc"))
        for i, n in enumerate(t["notes"]):
            c.add(n, setter(u["notes"], i))
        for i, v in enumerate(t["values"]):
            lab = v["label"]
            c.add(lab.title() if lab.isupper() else lab, setter(u["values"][i], "label"))
        u["lore"] = ""

    patch_uz = json.loads(json.dumps(patch_en))

    def notes(lst):
        for n in lst:
            c.add(n["t"], setter(n, "t"))
            c.add(n.get("info"), setter(n, "info"))

    for g in patch_uz["general"]:
        c.add(g["title"], setter(g, "title"))
        notes(g["notes"])
    for it in patch_uz["items"]:
        if it.get("general"):
            c.add(it["title"], setter(it, "title"))
        notes(it["notes"])
    for h in patch_uz["heroes"]:
        notes(h["notes"])
        notes(h["talents"])
        for a in h["abilities"]:
            notes(a["notes"])
        for f in h.get("facets", []):
            notes(f["notes"])
    for cr in patch_uz["creeps"]:
        notes(cr["notes"])

    c.run()

    for h in heroes:
        save(f"heroes/{h['id']}.json", h)
    save("items.uz.json", items_uz)
    save("patch.uz.json", patch_uz)
    log("O'zbekcha tayyor.")

    # Valve'ning ruscha patch notelarida tarjima qilinmagan inglizcha qatorlar bo'ladi -> ruschaga
    import re
    patch_ru = load("patch.ru.json")
    if patch_ru:
        rc = Collector()

        def ru_notes(lst):
            for n in lst:
                for k in ("t", "info"):
                    v = n.get(k)
                    if v and re.search(r"[A-Za-z]{3}", re.sub(r"<[^>]+>", "", v)) and not re.search(r"[А-Яа-я]", v):
                        rc.add(v, setter(n, k))

        for g in patch_ru["general"]:
            ru_notes(g["notes"])
        for it in patch_ru["items"]:
            ru_notes(it["notes"])
        for h in patch_ru["heroes"]:
            ru_notes(h["notes"]); ru_notes(h["talents"])
            for a in h["abilities"]:
                ru_notes(a["notes"])
        for cr in patch_ru["creeps"]:
            ru_notes(cr["notes"])
        log("Ruscha patch notelaridagi inglizcha qatorlar:")
        step = 400
        for i in range(0, len(rc.texts), step):
            res = translator.translate_many(rc.texts[i:i + step], "ru", src="en")
            for s, r in zip(rc.setters[i:i + step], res):
                s(r)
            translator.save_cache()
        save("patch.ru.json", patch_ru)
        log(f"  {len(rc.texts)} ta qator tarjima qilindi.")


if __name__ == "__main__":
    main()
