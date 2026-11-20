# Dota 2 Qo'llanma (uz / ru / en)

Patch 7.42 bo'yicha veb-ilova: geroylar, skillar, Aghanim's Scepter va Shard,
talantlar, buildlar (o'yin boshi, erta, o'rta va kech bosqich), sheriklar va kontr-piklar,
predmetlar, patch notelari va Steam yangiliklari.

## Ishga tushirish

Faqat Python 3.10+ kerak, qo'shimcha kutubxonalar talab qilinmaydi.

```powershell
python server.py
```

Keyin brauzerda oching: http://localhost:8080

## Internetdagi versiya (GitHub Pages, bepul)

Sayt `.github/workflows/deploy.yml` orqali GitHub Pages'ga joylanadi va o'zi yangilanadi:

* **har 3 soatda:** Steam yangiliklari olinadi va uz/ru/en ga tarjima qilinadi;
* **har kuni 03:30 UTC (08:30 Toshkent):** geroylar, predmetlar, patch notelari, buildlar va
  statistika qayta yig'iladi, so'ng o'zbekcha tarjima yangilanadi. Yangi patch yoki hotfix chiqsa,
  ertasi kuni saytga o'zi tushadi;
* **qo'lda:** GitHub → Actions → Deploy → Run workflow (`full` belgilansa hammasi yangilanadi).

Statistika patchning eng oxirgi o'yinlaridan olinadi (taxminan 2 mln o'yin), shuning uchun
hozirgi metani ko'rsatadi.

## Ma'lumotlarni qo'lda yangilash

```powershell
python tools/build_data.py --fresh
python tools/translate_uz.py
python tools/news.py
```

* `build_data.py` eng so'nggi patchni o'zi aniqlaydi (Valve datafeed). U geroy, skill, predmet
  va patch notelarini inglizcha va ruscha yuklaydi. OpenDota'dan buildlarni hamda shu patchdan
  keyingi reytingli o'yinlar statistikasini (g'alaba %, sheriklar, kontr-piklar) oladi.
  Statistikasiz, tezroq ishga tushirish uchun: `--no-stats`.
* `translate_uz.py` o'zbekcha versiyani avtomatik tarjima orqali yaratadi. Skill, predmet va
  geroy nomlari inglizcha qoladi. Tarjimalar `.cache/tr_uz.json` da saqlanadi.
* Tarjimani tuzatish uchun ikki fayl bor:
  * `data/uz_glossary.json`: hamma joyga qo'llanadigan almashtirishlar (regex), masalan
    "hayratda qoldiradi" → "stun qiladi".
  * `data/uz_overrides.json`: `{"inglizcha asl matn": "qo'lda yozilgan o'zbekcha"}`.

## Tuzilishi

```
server.py            veb-server + /api/news (Steam yangiliklari, 20 daqiqalik kesh, tarjima bilan)
web/                 interfeys (index.html, styles.css, app.js, i18n.js)
data/                yig'ilgan JSON ma'lumotlar
tools/               ma'lumot yig'ish va tarjima skriptlari
```

## Manbalar

* Valve: dota2.com/datafeed (geroylar, skillar, predmetlar, patch notelari)
* OpenDota API: buildlar (itemPopularity) va explorer orqali 7.42 o'yinlari
* Steam News API: yangiliklar
