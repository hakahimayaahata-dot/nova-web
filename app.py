from flask import Flask, request, redirect, render_template_string, abort
from urllib.parse import urlparse, quote_plus
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from html.parser import HTMLParser
import ipaddress
import socket

app = Flask(__name__)

# Safety: this demo fetches pages only from these public domains.
# Add domains you own or have permission to access.
ALLOWED_HOSTS = {"example.com", "www.example.com", "en.wikipedia.org", "www.wikipedia.org"}
MAX_BYTES = 1_000_000
TIMEOUT = 8

PAGE = """
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NOVA WEB</title>
<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; min-height:100vh; background:#0b1020; color:#e5e7eb;
       font:16px/1.6 system-ui,-apple-system,sans-serif; }
main { max-width:820px; margin:0 auto; padding:40px 18px; }
header { text-align:center; margin-bottom:28px; }
h1 { margin:0; font-size:clamp(2rem,7vw,3.3rem); letter-spacing:.08em; color:#60a5fa; }
.sub { color:#9ca3af; margin-top:4px; }
.card { background:#121a2d; border:1px solid #26334d; border-radius:16px; padding:20px; margin:16px 0; }
label { display:block; font-weight:650; margin-bottom:8px; }
.row { display:flex; gap:8px; }
input { min-width:0; flex:1; padding:13px 14px; border-radius:10px; border:1px solid #374151;
        background:#080d18; color:#fff; font:inherit; }
button { padding:12px 17px; border:0; border-radius:10px; background:#2563eb; color:white;
         font:inherit; font-weight:700; cursor:pointer; }
button:hover { background:#1d4ed8; }
.note { color:#aab4c5; font-size:.9rem; }
.error { color:#fca5a5; }
pre { white-space:pre-wrap; overflow-wrap:anywhere; background:#080d18; padding:16px; border-radius:10px; }
a { color:#93c5fd; }
@media(max-width:540px) { .row { flex-direction:column; } button { width:100%; } }
</style>
</head>
<body><main>
<header><h1>NOVA WEB</h1><div class="sub">Search · Read · Discover</div></header>
<section class="card">
<form action="/search" method="get">
<label for="q">DuckDuckGoで検索</label>
<div class="row"><input id="q" name="q" placeholder="検索ワードを入力…" required>
<button type="submit">検索</button></div>
<p class="note">検索結果はDuckDuckGoのサイトで開きます。</p>
</form>
</section>
<section class="card">
<form action="/view" method="get">
<label for="url">許可されたサイトのページ本文を取得</label>
<div class="row"><input id="url" name="url" type="url" placeholder="https://example.com/" required>
<button type="submit">本文を表示</button></div>
<p class="note">安全のため、このデモは example.com と Wikipedia の公開ページだけに対応します。HTMLをそのまま実行せず、読み取ったテキストだけを表示します。</p>
</form>
</section>
{% if error %}<section class="card error"><strong>エラー：</strong>{{ error }}</section>{% endif %}
{% if title %}<section class="card"><h2>{{ title }}</h2><p class="note">取得元：<a href="{{ source }}" rel="noreferrer">{{ source }}</a></p><pre>{{ body }}</pre></section>{% endif %}
<footer class="note">NOVA WEB demo · サーバー側取得は許可リスト内の公開ページに限定されています。</footer>
</main></body></html>
"""

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.title_parts = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in ("p", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\\n")

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if not self.skip_depth:
            clean = " ".join(data.split())
            if clean:
                self.parts.append(clean + " ")

class NoRedirectHandler(HTTPRedirectHandler):
    # Refuse redirects rather than following an unvalidated destination.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("リダイレクトには対応していません。リンク先URLを直接入力してください。")

def host_is_allowed(host):
    if not host:
        return False
    host = host.lower().rstrip(".")
    return host in ALLOWED_HOSTS

def validate_url(raw_url):
    parsed = urlparse(raw_url)
    if parsed.scheme != "https":
        raise ValueError("HTTPSのURLを入力してください。")
    if parsed.username or parsed.password:
        raise ValueError("ユーザー名やパスワードを含むURLには対応していません。")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host_is_allowed(host):
        raise ValueError("このデモで取得できるのは example.com と Wikipedia のみです。")
    # Resolve and reject private, loopback, link-local, reserved, or multicast IPs.
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError("ホスト名を解決できませんでした。")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError("公開インターネット上のIPアドレス以外には接続できません。")
    return raw_url

@app.get("/")
def home():
    return render_template_string(PAGE, error=None, title=None, body=None, source=None)

@app.get("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect("/")
    return redirect("https://duckduckgo.com/?q=" + quote_plus(q), code=302)

@app.get("/view")
def view():
    raw_url = request.args.get("url", "").strip()
    try:
        url = validate_url(raw_url)
        req = Request(url, headers={"User-Agent": "NOVA-Web-Demo/1.0", "Accept": "text/html,text/plain"})
        opener = build_opener(NoRedirectHandler())
        with opener.open(req, timeout=TIMEOUT) as response:
            final_url = response.geturl()
            content_type = response.headers.get_content_type()
            if content_type not in ("text/html", "text/plain"):
                raise ValueError("HTMLまたはプレーンテキストのページだけ表示できます。")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("ページが大きすぎます（上限1 MB）。")
            charset = response.headers.get_content_charset() or "utf-8"
        html = data.decode(charset, errors="replace")
        if content_type == "text/html":
            parser = TextExtractor()
            parser.feed(html)
            title = " ".join(" ".join(parser.title_parts).split()) or final_url
            body = " ".join("".join(parser.parts).split())
        else:
            title, body = final_url, html
        if len(body) > 20000:
            body = body[:20000] + "\\n…（表示を省略しました）"
        return render_template_string(PAGE, error=None, title=title, body=body, source=final_url)
    except Exception as exc:
        return render_template_string(PAGE, error=str(exc), title=None, body=None, source=None), 400

if __name__ == "__main__":
    # Local development only. Do not expose the Flask development server directly to the internet.
    app.run(host="127.0.0.1", port=5000, debug=False)
