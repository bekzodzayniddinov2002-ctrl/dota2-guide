"""Umumiy yordamchilar: HTTP, kesh, matn formatlash."""
import json
import os
import re
import time
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, ".cache")
UA = "Mozilla/5.0 (DotaGuideUZ data builder)"


def fetch_json(url, retries=4, timeout=60, pause=0.0):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            if pause:
                time.sleep(pause)
            return data
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as e:
            last = e
            time.sleep(2 + i * 3)
    raise RuntimeError(f"fetch failed: {url}: {last}")


def cached_json(key, url, **kw):
    """Disk keshi: bir xil manbani qayta yuklamaslik uchun."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r"[^a-zA-Z0-9_.-]", "_", key) + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    data = fetch_json(url, **kw)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def save(rel, obj):
    path = os.path.join(DATA, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def load(rel, default=None):
    path = os.path.join(DATA, rel)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt_num(v):
    if v is None:
        return ""
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    return ("%.2f" % v).rstrip("0").rstrip(".")


def join_vals(vals, pct=False):
    vals = [fmt_num(v) for v in vals]
    if vals and all(v == vals[0] for v in vals):
        vals = vals[:1]
    s = " / ".join(vals)
    return s + ("%" if pct and s else "")


def special_map(ability):
    """special_values -> {nom: matn qiymat}"""
    out = {}
    for sv in ability.get("special_values", []) or []:
        out[sv["name"].lower()] = sv
    return out


def fill_placeholders(text, ability, mode=None, extra=None):
    """%name% va %%  belgilarini haqiqiy qiymatlar bilan almashtiradi.
    mode="scepter"/"shard" bo'lsa, Aghanim qiymatlari ustun turadi."""
    if not text:
        return ""
    sm = dict(extra or {})
    sm.update(special_map(ability))

    def rep(m):
        key = m.group(1)
        if key == "":
            return "%"
        sv = sm.get(key.lower())
        if sv is None:
            # Ba'zi kalitlar Ability* ko'rinishida bo'ladi
            for k, v in sm.items():
                if k.endswith(key.lower()):
                    sv = v
                    break
        if sv is None and key.lower().startswith(("bonus_", "scepter_", "shard_")):
            # %bonus_rot_radius% -> rot_radius ning Scepter/Shard qiymati
            k2 = re.sub(r"^(bonus_|scepter_|shard_)", "", key.lower())
            sv2 = sm.get(k2)
            if sv2 is not None:
                alt = sv2.get("values_" + (mode or "scepter")) or sv2.get("values_shard") or sv2.get("values_scepter")
                if alt:
                    return join_vals(alt)
                sv = sv2
        if sv is None:
            return "?"
        base = sv.get("values_float") or []
        if mode and sv.get("values_" + mode):
            return join_vals(sv["values_" + mode])
        if base and all(abs(v) < 1e-9 for v in base):
            alt = sv.get("values_scepter") or sv.get("values_shard")
            if alt:
                return join_vals(alt)
        return join_vals(base)

    text = re.sub(r"%([a-zA-Z0-9_]*)%", rep, text)
    return text


STAT_TOKENS = {
    "en": {"str": "Strength", "agi": "Agility", "int": "Intelligence", "all": "All Attributes",
           "damage": "Damage", "attack": "Attack Speed", "armor": "Armor", "health": "Health",
           "mana": "Mana", "hp_regen": "Health Regen", "health_regen": "Health Regen", "mana_regen": "Mana Regen",
           "move_speed": "Movement Speed", "evasion": "Evasion", "spell_amp": "Spell Amplification",
           "magic_resist": "Magic Resistance", "selected_attrib": "Primary Attribute", "selected_attribute": "Primary Attribute",
           "attack_range": "Attack Range", "lifesteal": "Lifesteal", "spell_lifesteal": "Spell Lifesteal",
           "cast_range": "Cast Range", "base_attack_time": "Base Attack Time", "attack_pct": "Attack Speed",
           "manacost_reduction": "Mana Cost Reduction", "cooldown_reduction": "Cooldown Reduction",
           "status_resist": "Status Resistance", "slow_resist": "Slow Resistance", "debuff_amp": "Debuff Amplification",
           "projectile_speed": "Projectile Speed", "vision": "Vision", "night_vision": "Night Vision",
           "hp_regen_amp": "Health Regen Amplification", "heal_amp": "Heal Amplification"},
    "ru": {"str": "к силе", "agi": "к ловкости", "int": "к интеллекту", "all": "ко всем атрибутам",
           "damage": "к урону", "attack": "к скорости атаки", "armor": "к броне", "health": "к здоровью",
           "mana": "к мане", "hp_regen": "к восст. здоровья", "health_regen": "к восст. здоровья",
           "mana_regen": "к восст. маны", "move_speed": "к скорости передвижения", "evasion": "к уклонению",
           "spell_amp": "к усилению способностей", "magic_resist": "к сопротивлению магии",
           "selected_attrib": "к основному атрибуту", "selected_attribute": "к основному атрибуту",
           "attack_range": "к дальности атаки", "lifesteal": "к вампиризму", "spell_lifesteal": "к вампиризму заклинаний",
           "cast_range": "к дальности применения", "attack_pct": "к скорости атаки",
           "manacost_reduction": "к снижению затрат маны", "cooldown_reduction": "к снижению перезарядки",
           "status_resist": "к сопротивлению эффектам", "slow_resist": "к сопротивлению замедлению",
           "projectile_speed": "к скорости снарядов", "vision": "к обзору", "night_vision": "к ночному обзору",
           "hp_regen_amp": "к усилению восст. здоровья", "heal_amp": "к усилению лечения"},
}


def stat_label(label, lang):
    m = STAT_TOKENS.get(lang, STAT_TOKENS["en"])
    return re.sub(r"\$([a-z_]+)", lambda x: m.get(x.group(1), STAT_TOKENS["en"].get(x.group(1), x.group(1).replace("_", " ").title())), label or "").strip()


def clean_html(text):
    """Faqat xavfsiz teglar qoladi: b, br, h1 -> strong."""
    if not text:
        return ""
    text = text.replace("\\n", "<br>").replace("\n", "<br>")
    text = re.sub(r"<h1>(.*?)</h1>", r"<strong class='h'>\1</strong><br>", text, flags=re.S)
    text = re.sub(r"<span[^>]*>(.*?)</span>", r"<b>\1</b>", text, flags=re.S)
    text = re.sub(r"<(?!/?(b|br|strong)\b)[^>]+>", "", text)
    text = re.sub(r"(<br>\s*){3,}", "<br><br>", text)
    return text.strip()
