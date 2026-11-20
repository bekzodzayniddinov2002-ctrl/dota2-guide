"""Dota 2 Qo'llanma — lokal veb-server (faqat Python standart kutubxonasi).

    python server.py            ->  http://localhost:8080

Internetdagi versiya (GitHub Pages) serversiz ishlaydi: web/ va data/ statik fayllar sifatida
joylanadi, yangiliklar esa tools/news.py orqali data/news.*.json ga yoziladi.
Bu server lokal sinov uchun: /api/news so'rovida yangiliklarni jonli yuklaydi.
"""
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import news  # noqa: E402

WEB = os.path.join(ROOT, "web")
DATA = os.path.join(ROOT, "data")
NEWS_TTL = 20 * 60
_news = {"t": 0, "raw": [], "lang": {}}
_lock = threading.Lock()


def news_for(lang):
    with _lock:
        if time.time() - _news["t"] > NEWS_TTL or not _news["raw"]:
            _news.update(t=time.time(), raw=news.fetch_raw(), lang={})
        if lang not in _news["lang"]:
            _news["lang"][lang] = news.localize(_news["raw"], lang)
        return _news["lang"][lang]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, fmt, *args):
        if "/api/" in str(args[0] if args else ""):
            sys.stderr.write("%s\n" % (fmt % args))

    def translate_path(self, path):
        p = urllib.parse.urlparse(path).path
        if p.startswith("/data/"):
            rel = os.path.normpath(urllib.parse.unquote(p[len("/data/"):])).lstrip("\\/")
            if rel.startswith(".."):
                return os.path.join(WEB, "404")
            return os.path.join(DATA, rel)
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/news":
            lang = urllib.parse.parse_qs(u.query).get("lang", ["uz"])[0]
            if lang not in news.LANGS:
                lang = "uz"
            try:
                return self._json({"items": news_for(lang)})
            except Exception as e:  # noqa
                return self._json({"items": [], "error": str(e)}, 502)
        return super().do_GET()


def main():
    port = int(os.environ.get("PORT", "8080"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Dota 2 Qo'llanma: http://localhost:{port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
