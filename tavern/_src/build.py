#!/usr/bin/env python3
"""Трактирная книга — сборщик статичного сайта из экспорта Telegram-канала.

Запуск (из корня репозитория):

    python tavern/_src/build.py                       # пересобрать страницы из уже импортированных постов
    python tavern/_src/build.py --export "E:\\путь\\ChatExport_2026-09-26"   # импортировать экспорт и собрать

Экспорт делается в Telegram Desktop: канал → ⋮ → Экспорт истории чата.
Подходят оба формата: «Машиночитаемый JSON» (result.json) и HTML (messages*.html).

Что куда:
  _src/config.json        — название, ссылка на канал, комнаты и их хэштеги
  _src/catalog/*.json     — каталоги (забивки, растения, миниатюры, полка, ярлыки ИИ), правятся руками
  _src/posts.json         — посты канала после импорта (создаётся сам)
  _src/pixel_scene.py     — рисует пиксельный зал (assets/scene/*, hotspots.json)
  tavern/*.html, scroll/  — готовые страницы (генерируются, руками не править)
"""
import argparse
import datetime as dt
import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SRC = Path(__file__).resolve().parent
SITE = SRC.parent  # папка tavern/
MEDIA_DIR = SITE / "media" / "tg"

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
RATING_WORDS = {1: "чума", 2: "ересь", 3: "сносно", 4: "добро", 5: "благодать"}
HASHTAG_RE = re.compile(r"#([0-9A-Za-zА-Яа-яЁё_]+)")
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
QUOTES = [
    "Всяк сюда входящий — вытри ноги и надежду.",
    "Трактирщик не виноват. Виноваты звёзды и понедельник.",
    "Улитка снова победила рыцаря. Летописец плачет.",
    "Эль тёплый, свечи коптят, Wi-Fi через раз. Средневековье.",
    "Здесь могла быть ваша чума.",
    "Писано при лучине, дрожащей от сквозняка.",
]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def ru_date(iso):
    if not iso:
        return ""
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def load_json(path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ───────────────────────── импорт экспорта ─────────────────────────

def plain_to_entities(text):
    """Разбивает простой текст на сущности: обычный текст, хэштеги, ссылки."""
    out, pos = [], 0
    token_re = re.compile(HASHTAG_RE.pattern + "|" + URL_RE.pattern)
    for m in token_re.finditer(text):
        if m.start() > pos:
            out.append({"type": "plain", "text": text[pos:m.start()]})
        tok = m.group(0)
        out.append({"type": "hashtag" if tok.startswith("#") else "link", "text": tok})
        pos = m.end()
    if pos < len(text):
        out.append({"type": "plain", "text": text[pos:]})
    return out


def json_text_to_entities(msg):
    ents = msg.get("text_entities")
    if ents is None:
        raw = msg.get("text", "")
        if isinstance(raw, str):
            return plain_to_entities(raw)
        ents = [x if isinstance(x, dict) else {"type": "plain", "text": x} for x in raw]
    return [{k: v for k, v in e.items() if k in ("type", "text", "href")} for e in ents]


def usable_path(p):
    return isinstance(p, str) and p and not p.startswith("(")


def json_message_media(msg):
    for key in ("photo",):
        if usable_path(msg.get(key)):
            return [msg[key]]
    if usable_path(msg.get("file")) and str(msg.get("mime_type", "")).startswith("image/"):
        return [msg["file"]]
    if usable_path(msg.get("thumbnail")):
        return [msg["thumbnail"]]
    return []


def import_json(path):
    data = json.load(open(path, encoding="utf-8"))
    raw = []
    for m in data.get("messages", []):
        if m.get("type") != "message":
            continue
        raw.append({
            "id": m["id"],
            "date": m.get("date", "")[:19],
            "ts": int(m.get("date_unixtime") or 0) or int(dt.datetime.fromisoformat(m["date"][:19]).timestamp()),
            "entities": json_text_to_entities(m),
            "photos": json_message_media(m),
        })
    return data.get("name", ""), raw


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs), [], parent

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def iter(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.iter()

    def find_all(self, tag=None, cls=None):
        return [n for n in self.iter() if (tag is None or n.tag == tag) and (cls is None or cls in n.classes)]

    def find(self, tag=None, cls=None):
        r = self.find_all(tag, cls)
        return r[0] if r else None


VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr"}


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


STYLE_TAGS = {"b": "bold", "strong": "bold", "i": "italic", "em": "italic", "u": "underline",
              "s": "strikethrough", "del": "strikethrough", "code": "code", "pre": "pre",
              "blockquote": "blockquote"}


def html_node_to_entities(node, style=None, out=None):
    out = [] if out is None else out
    for c in node.children:
        if isinstance(c, str):
            if c:
                out.append({"type": style or "plain", "text": c})
            continue
        if c.tag == "br":
            out.append({"type": "plain", "text": "\n"})
        elif c.tag == "a":
            text = "".join(t for t in _texts(c))
            onclick = c.attrs.get("onclick", "")
            href = c.attrs.get("href", "")
            if "ShowHashtag" in onclick or text.startswith("#"):
                out.append({"type": "hashtag", "text": text})
            elif href.startswith(("http://", "https://", "tg://")):
                out.append({"type": "text_link", "text": text, "href": href})
            else:
                out.append({"type": style or "plain", "text": text})
        elif "spoiler" in c.classes:
            html_node_to_entities(c, "spoiler", out)
        else:
            html_node_to_entities(c, STYLE_TAGS.get(c.tag, style), out)
    return out


def _texts(node):
    for c in node.children:
        if isinstance(c, str):
            yield c
        elif c.tag == "br":
            yield "\n"
        else:
            yield from _texts(c)


def import_html(folder):
    files = sorted(folder.glob("messages*.html"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 1))
    raw, name = [], ""
    for f in files:
        tb = TreeBuilder()
        tb.feed(f.read_text(encoding="utf-8"))
        if not name:
            hdr = tb.root.find(cls="page_header")
            if hdr:
                name = "".join(_texts(hdr)).strip()
        for msg in tb.root.find_all("div", "message"):
            if "default" not in msg.classes:
                continue
            mid = int(re.sub(r"\D", "", msg.attrs.get("id", "0")) or 0)
            date_el = msg.find(cls="date")
            stamp = (date_el.attrs.get("title", "") if date_el else "").split(" UTC")[0]
            try:
                d = dt.datetime.strptime(stamp, "%d.%m.%Y %H:%M:%S")
            except ValueError:
                continue
            text_el = next((n for n in msg.find_all("div", "text")), None)
            ents = html_node_to_entities(text_el) if text_el else []
            if ents:
                ents[0]["text"] = ents[0]["text"].lstrip()
                ents[-1]["text"] = ents[-1]["text"].rstrip()
            photos = [a.attrs["href"] for a in msg.find_all("a", "photo_wrap") if a.attrs.get("href")]
            if not photos:
                thumbs = [i.attrs.get("src") for i in msg.find_all("img", "video_file")]
                photos = [t for t in thumbs if t]
            raw.append({"id": mid, "date": d.isoformat(), "ts": int(d.timestamp()),
                        "entities": ents, "photos": photos})
    return name, raw


def group_albums(raw):
    """Альбом в экспорте — это несколько сообщений с одной датой. Склеиваем их в один пост."""
    posts = []
    for m in sorted(raw, key=lambda x: x["id"]):
        has_text = bool("".join(e["text"] for e in m["entities"]).strip())
        prev = posts[-1] if posts else None
        if prev and abs(m["ts"] - prev["ts"]) <= 1 and (not has_text or not prev["_has_text"]):
            prev["photos"] += m["photos"]
            if has_text:
                prev["entities"], prev["_has_text"] = m["entities"], True
            continue
        posts.append(dict(m, _has_text=has_text))
    return [p for p in posts if p["_has_text"] or p["photos"]]


def copy_media(export_dir, posts, max_per_post=6):
    try:
        from PIL import Image
    except ImportError:
        Image = None
        print("  (Pillow не установлен — картинки копируются без сжатия: pip install pillow)")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for p in posts:
        local = []
        for rel in p["photos"][:max_per_post]:
            src = export_dir / rel
            if not src.exists():
                continue
            name = re.sub(r"[^\w.@-]", "_", src.name)
            if Image:
                name = Path(name).stem + ".jpg"
            dst = MEDIA_DIR / name
            if not dst.exists():
                if Image:
                    try:
                        im = Image.open(src)
                        im.thumbnail((1200, 1200))
                        im.convert("RGB").save(dst, "JPEG", quality=82, optimize=True)
                    except Exception:
                        shutil.copy2(src, dst)
                else:
                    shutil.copy2(src, dst)
                copied += 1
            local.append(f"media/tg/{name}")
        p["photos"] = local
    print(f"  картинок скопировано: {copied}")


def run_import(export_dir, skip_media):
    export_dir = Path(export_dir)
    if (export_dir / "result.json").exists():
        name, raw = import_json(export_dir / "result.json")
        fmt = "JSON"
    elif list(export_dir.glob("messages*.html")):
        name, raw = import_html(export_dir)
        fmt = "HTML"
    else:
        sys.exit(f"В папке {export_dir} нет ни result.json, ни messages.html")
    posts = group_albums(raw)
    print(f"Импорт ({fmt}): канал «{name}», сообщений {len(raw)}, постов после склейки альбомов {len(posts)}")
    if skip_media:
        for p in posts:
            p["photos"] = []
    else:
        copy_media(export_dir, posts)
    for p in posts:
        p.pop("_has_text", None)
        p.pop("ts", None)
    with open(SRC / "posts.json", "w", encoding="utf-8") as f:
        json.dump({"channel": name, "imported": dt.date.today().isoformat(), "posts": posts},
                  f, ensure_ascii=False, indent=1)


# ───────────────────────── подготовка постов ─────────────────────────

def load_posts():
    data = load_json(SRC / "posts.json")
    if data is None:
        data = load_json(SRC / "sample_posts.json")
        for p in data["posts"]:
            p["entities"] = plain_to_entities(p.pop("text"))
        print("posts.json не найден — собираю на образцах (sample_posts.json)")
    return data["posts"]


def strip_tags_line(line):
    return HASHTAG_RE.sub("", line).strip(" \t—-–:|•·")


def enrich(posts, rooms):
    tag_to_rooms = {}
    for r in rooms:
        for t in r["hashtags"]:
            tag_to_rooms.setdefault(t.lower(), []).append(r["id"])
    for p in posts:
        text = "".join(e["text"] for e in p["entities"])
        p["text"] = text
        p["hashtags"] = list(dict.fromkeys(t.lower() for t in HASHTAG_RE.findall(text)))
        p["rooms"] = list(dict.fromkeys(rid for t in p["hashtags"] for rid in tag_to_rooms.get(t, [])))
        # заголовок — первая строка, в которой есть что-то кроме хэштегов
        title, cut, offset = "", 0, 0
        for line in text.split("\n"):
            offset += len(line) + 1
            if strip_tags_line(line):
                title, cut = strip_tags_line(line), offset
                break
        if not title:
            title = "Свиток без слов" if p["photos"] else "Пустой свиток"
        if len(title) > 110:  # длинная первая строка: заголовок обрезаем, а текст показываем целиком
            title, cut = title[:105].rsplit(" ", 1)[0] + "…", 0
        p["title"] = title
        p["_cut"] = cut
        body = text.rstrip()
        while body and "#" in body.rsplit("\n", 1)[-1] and not strip_tags_line(body.rsplit("\n", 1)[-1]):
            body = body.rsplit("\n", 1)[0].rstrip() if "\n" in body else ""
        p["_end"] = max(len(body), cut)
        rest = HASHTAG_RE.sub("", text[cut:])
        rest = re.sub(r"\s+", " ", rest).strip()
        p["excerpt"] = rest if len(rest) <= 240 else rest[:230].rsplit(" ", 1)[0] + "…"
        p["search"] = (title + " " + rest + " " + " ".join(p["hashtags"])).lower()
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def render_entities(entities, root, skip=0, end=None):
    """Сущности Telegram → безопасный HTML. skip — сколько символов пропустить (заголовок),
    end — где оборвать (хвост из одних хэштегов показывается метками под текстом)."""
    out, pos = [], 0
    for e in entities:
        t, s = e.get("type", "plain"), e.get("text", "")
        if end is not None:
            if pos >= end:
                break
            if pos + len(s) > end:
                s = s[:end - pos]
            pos += len(e.get("text", ""))
        if skip:
            if len(s) <= skip:
                skip -= len(s)
                continue
            s, skip = s[skip:], 0
            if t in ("hashtag", "link", "text_link", "mention"):
                t = "plain"
        if not s:
            continue
        x = esc(s)
        if t != "pre":
            x = x.replace("\n", "<br>\n")
        if t == "bold":
            out.append(f"<b>{x}</b>")
        elif t == "italic":
            out.append(f"<i>{x}</i>")
        elif t == "underline":
            out.append(f"<u>{x}</u>")
        elif t == "strikethrough":
            out.append(f"<s>{x}</s>")
        elif t == "code":
            out.append(f"<code>{x}</code>")
        elif t == "pre":
            out.append(f"<pre><code>{x}</code></pre>")
        elif t == "blockquote":
            out.append(f"<blockquote>{x}</blockquote>")
        elif t == "spoiler":
            out.append(f'<span class="spoiler" tabindex="0">{x}</span>')
        elif t == "hashtag":
            tag = s.lstrip("#").lower()
            out.append(f'<a class="htag" href="{root}search.html?tag={esc(tag)}">{x}</a>')
        elif t in ("link", "url"):
            href = s if re.match(r"^(https?|tg)://", s) else "https://" + s
            out.append(f'<a href="{esc(href)}" rel="nofollow noopener" target="_blank">{x}</a>')
        elif t == "text_link" and re.match(r"^(https?|tg)://", e.get("href", "")):
            out.append(f'<a href="{esc(e["href"])}" rel="nofollow noopener" target="_blank">{x}</a>')
        elif t == "mention":
            out.append(f'<a href="https://t.me/{esc(s.lstrip("@"))}" rel="noopener" target="_blank">{x}</a>')
        elif t == "email":
            out.append(f'<a href="mailto:{x}">{x}</a>')
        else:
            out.append(x)
    body = "".join(out).strip()
    return re.sub(r"^(<br>\s*)+", "", body)


# ───────────────────────── общий макет ─────────────────────────

class Site:
    def __init__(self, cfg, posts, catalogs):
        self.cfg, self.s, self.rooms = cfg, cfg["site"], cfg["rooms"]
        self.posts, self.cat = posts, catalogs
        self.by_id = {p["id"]: p for p in posts}
        self.room_posts = {r["id"]: [p for p in posts if r["id"] in p["rooms"]] for r in self.rooms}
        self.today = dt.date.today()
        self.sample = any(p.get("sample") for p in posts)

    def tg_link(self, pid):
        u = self.s.get("channel_username", "").lstrip("@")
        return f"https://t.me/{u}/{pid}" if u and pid else ""

    def post_link(self, pid, root=""):
        if pid in self.by_id:
            return f"{root}scroll/{pid}.html"
        return self.tg_link(pid)

    def page(self, path, title, body, root="", room=None, desc="", scene=False):
        s = self.s
        full_title = f"{title} — {s['title']}" if title != s["title"] else s["title"]
        nav = "".join(
            f'<a class="plank{" is-here" if room == r["id"] else ""}" href="{root}{r["page"]}">'
            f'<span>{esc(r["sign"])}</span><small>#{esc(r["hashtags"][0])}</small></a>'
            for r in self.rooms)
        metrika = ""
        if s.get("yandex_metrika"):
            mid = int(s["yandex_metrika"])
            metrika = f"""<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();for(var j=0;j<document.scripts.length;j++){{if(document.scripts[j].src===r){{return;}}}}k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,'script','https://mc.yandex.ru/metrika/tag.js?id={mid}','ym');ym({mid},'init',{{ssr:true,clickmap:true,trackLinks:true,accurateTrackBounce:true}});</script>"""
        neighbors = "".join(f'<a href="{esc(n["url"])}">{esc(n["title"])}</a>' for n in s.get("neighbors", []))
        chan = esc(s["channel_url"])
        sample_note = ('<div class="sample-bar">Трактир обставлен <b>образцами</b>: '
                       'настоящие посты появятся после импорта экспорта канала.</div>') if self.sample else ""
        canonical = s["base_url"] + (path if path != "index.html" else "")
        html_out = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc or s['tagline'])}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc or s['tagline'])}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="theme-color" content="#1b120c">
<link rel="icon" href="{root}assets/favicon.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Ruslan+Display&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&family=PT+Mono&family=Pixelify+Sans:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/tavern.css">
{metrika}
</head>
<body class="{'is-hall' if scene else 'is-room'}{' room-' + room if room else ''}">
<a class="skip" href="#main">К содержимому</a>
<div class="torchlight" aria-hidden="true"></div>
<header class="top">
  <a class="sign" href="{root}index.html" title="В общий зал">
    <span class="sign-chain" aria-hidden="true"></span>
    <span class="sign-board"><span class="sign-small">{esc(s['channel_title'])}</span>{esc(s['title'])}</span>
  </a>
  <nav class="planks" aria-label="Комнаты трактира">{nav}<a class="plank plank-search{' is-here' if room == 'search' else ''}" href="{root}search.html"><span>Писарь</span><small>поиск</small></a></nav>
</header>
{sample_note}
<main id="main">
{body}
</main>
<footer class="bottom">
  <div class="foot-grid">
    <section class="box">
      <h3>Грамота</h3>
      <p>Сие есть архив канала <a href="{chan}">{esc(s['channel_title'])}</a>. Лента в Telegram течёт и тонет, а здесь всё лежит по полкам.</p>
      <p class="quote" data-quotes='{esc(json.dumps(QUOTES, ensure_ascii=False))}'>{esc(QUOTES[0])}</p>
    </section>
    <section class="box">
      <h3>Свечной счётчик</h3>
      <p class="candles" aria-live="polite"><span class="candle-row" aria-hidden="true"></span><span class="candle-text">Ты здесь впервые, путник.</span></p>
      <p class="tiny">Свечи считаются только в твоём браузере. Мы не шпионим, мы страдаем.</p>
    </section>
    <section class="box">
      <h3>Трактовое кольцо</h3>
      <p class="ring">{neighbors}<a href="{chan}">Канал в Telegram</a><a href="{root}sitemap.xml">Карта трактира</a></p>
      <div class="buttons88" aria-hidden="true">
        <span class="b88 b-a">лучше смотреть<br>при лучине</span>
        <span class="b88 b-b">сделано<br>гусиным пером</span>
        <span class="b88 b-c">без чумы<br>и NFT</span>
        <span class="b88 b-d">HTML 1.0<br>ANNO 2026</span>
      </div>
    </section>
  </div>
  <p class="colophon">Переписано писарем {self.today.year} года от Р. Х. · <a href="{root}index.html">общий зал</a> · <a href="#main">наверх ↑</a></p>
</footer>
<script src="{root}assets/tavern.js"></script>
</body>
</html>
"""
        out = SITE / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html_out, encoding="utf-8")

    # ─────────── маленькие детали ───────────

    def initial_art(self, p, root):
        """Буквица вместо картинки: большая первая буква заголовка в цветной рамке."""
        letter = next((ch for ch in p["title"] if ch.isalnum()), "Ѣ").upper()
        hue = (p["id"] * 47) % 360
        return (f'<div class="initial" style="--h:{hue}" aria-hidden="true"><span>{esc(letter)}</span></div>')

    def post_card(self, p, root="", big=False):
        img = (f'<img src="{root}{esc(p["photos"][0])}" alt="" loading="lazy">' if p["photos"]
               else self.initial_art(p, root))
        tags = "".join(f'<a class="chip chip-sm" href="{root}search.html?tag={esc(t)}">#{esc(t)}</a>' for t in p["hashtags"][:5])
        stamp = '<span class="stamp">образец</span>' if p.get("sample") else ""
        tg = self.tg_link(p["id"])
        tg_a = f' · <a href="{esc(tg)}" rel="noopener" target="_blank">в канал ↗</a>' if tg else ""
        return f"""<article class="card post{' post-big' if big else ''}" data-search="{esc(p['search'])}" data-tags="{esc(' '.join(p['hashtags']))}" data-date="{esc(p['date'])}">
  <a class="post-pic" href="{root}scroll/{p['id']}.html" tabindex="-1" aria-hidden="true">{img}</a>
  <div class="post-body">{stamp}
    <h3><a href="{root}scroll/{p['id']}.html">{esc(p['title'])}</a></h3>
    <p class="meta"><time datetime="{esc(p['date'])}">{ru_date(p['date'])}</time>{tg_a}</p>
    <p class="excerpt">{esc(p['excerpt'])}</p>
    <p class="tags">{tags}</p>
  </div>
</article>"""

    def feed(self, posts, root="", title="Свитки из канала", big=False, empty=None):
        if not posts:
            return f'<section class="parchment"><h2>{esc(title)}</h2><p class="empty">{esc(empty or "Свиток пуст. Писарь запил.")}</p></section>'
        counts = {}
        for p in posts:
            for t in p["hashtags"]:
                counts[t] = counts.get(t, 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:24]
        chips = "".join(f'<button type="button" class="chip" data-facet="tags" data-value="{esc(t)}">#{esc(t)} <sup>{n}</sup></button>' for t, n in top)
        cards = "\n".join(self.post_card(p, root, big) for p in posts)
        return f"""<section class="parchment feed" id="feed">
  <h2>{esc(title)} <small class="count" data-count-for="feed-list">{len(posts)}</small></h2>
  <div class="filterbox" data-target="#feed-list" data-page="12">
    <label class="search-field"><span>Искать в свитках</span><input type="search" data-search placeholder="например: мята, агент, Берсерк…"></label>
    <div class="chips" data-mode="all" data-group="tags">{chips}</div>
    <div class="row-controls">
      <label>Порядок <select data-sort><option value="date-desc">сначала новые</option><option value="date-asc">сначала старые</option></select></label>
      <button type="button" class="btn-link" data-reset>сбросить</button>
    </div>
  </div>
  <div class="cards" id="feed-list">
{cards}
  </div>
  <p class="nothing" hidden>Ничего не нашлось. Попробуй иначе, путник.</p>
  <button type="button" class="btn more" data-more="#feed-list">Ещё свитков</button>
</section>"""

    def room_head(self, r):
        n = len(self.room_posts[r["id"]])
        tags = " ".join(f"#{t}" for t in r["hashtags"][:4])
        return f"""<section class="room-head">
  <div class="marginalia marg-{r['id']}" aria-hidden="true"><img class="pix" src="assets/scene/icon-{r['id']}.png" alt=""></div>
  <div>
    <p class="crumbs"><a href="index.html">Общий зал</a> › {esc(r['name'])}</p>
    <h1>{esc(r['name'])}</h1>
    <p class="epigraph">{esc(r['epigraph'])}</p>
    <p class="about">{esc(r['about'])}</p>
    <p class="meta">{n} {plural(n, 'свиток', 'свитка', 'свитков')} в канале · <span class="mono">{esc(tags)}</span></p>
  </div>
</section>"""


def plural(n, one, few, many):
    n = abs(n) % 100
    if 10 < n < 20:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


def pips(v, kind, label):
    v = int(v or 0)
    dots = "".join(f'<i class="{"on" if i < v else ""}"></i>' for i in range(5))
    return f'<span class="pips pips-{kind}" title="{esc(label)}: {v} из 5" aria-label="{esc(label)}: {v} из 5">{dots}</span>'


def rating_badge(v):
    v = int(v or 0)
    return f'<span class="rating r{v}" title="{v} из 5">{"✦" * v}{"✧" * (5 - v)} <b>{RATING_WORDS.get(v, "")}</b></span>'


def stamp(item):
    return '<span class="stamp">образец</span>' if item.get("example") else ""


def facet_chips(values, facet, mode="any", label=None):
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    chips = "".join(f'<button type="button" class="chip" data-facet="{facet}" data-value="{esc(v)}">{esc(v)} <sup>{n}</sup></button>'
                    for v, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    lab = f'<span class="chips-label">{esc(label)}</span>' if label else ""
    return f'<div class="chips" data-mode="{mode}" data-group="{facet}">{lab}{chips}</div>'


# ───────────────────────── страницы ─────────────────────────

def pixel_scene_html(site):
    """Пиксельный зал: кадры анимации, подсветки и кликабельные зоны из hotspots.json."""
    spots = load_json(SRC / "hotspots.json")
    sw, sh = spots["size"]
    rooms = {r["id"]: r for r in site.rooms}
    targets = {
        "garden": "garden", "shelf": "shelf", "search": None, "channel": None,
        "ai": "ai", "minis": "minis", "hookah": "hookah",
    }
    order = ["channel", "garden", "shelf", "search", "ai", "minis", "hookah"]  # кальян поверх низа полки
    hls, links = [], []
    for key in order:
        if key not in spots["hot"]:
            continue
        x0, y0, x1, y1 = spots["hot"][key]
        rid = targets.get(key)
        if rid in rooms:
            r = rooms[rid]
            href, name, n = r["page"], r["sign"], len(site.room_posts[rid])
            aria = f'{r["name"]}: {n} {plural(n, "свиток", "свитка", "свитков")}'
        elif key == "search":
            href, name, n = "search.html", "Картотека", len(site.posts)
            aria = f"Картотека писаря: поиск по {n} свиткам"
        else:
            href, name, n = site.s["channel_url"], "Канал", None
            aria = f"Канал {site.s['channel_title']} в Telegram"
        style = (f"left:{x0 / sw * 100:.3f}%;top:{y0 / sh * 100:.3f}%;"
                 f"width:{(x1 - x0) / sw * 100:.3f}%;height:{(y1 - y0) / sh * 100:.3f}%")
        count = f" <b>{n}</b>" if n is not None else " <b>↗</b>"
        hls.append(f'<img class="pix-hl" data-hl="{key}" src="assets/scene/hl-{key}.png" alt="">')
        links.append(f'<a class="pix-hot" data-room="{key}" href="{esc(href)}" style="{style}" aria-label="{esc(aria)}">'
                     f'<span class="pix-label">{esc(name)}{count}</span></a>')
    snail = (f"left:{300 / sw * 100:.3f}%;top:{256 / sh * 100:.3f}%;"
             f"width:{56 / sw * 100:.3f}%;height:{22 / sh * 100:.3f}%")
    return f"""<div class="pix-scene" role="group" aria-label="Общий зал Лисьей таверны: окно с огородом, книжная полка, очаг, доска объявлений, стол алхимика с магическим шаром, шкаф с оловянными воинами и лис с кальяном">
      <div class="pix-film" aria-hidden="true"><img src="assets/scene/frames.png" alt="" width="{sw * 4}" height="{sh}"></div>
      {''.join(hls)}
      {''.join(links)}
      <button type="button" class="pix-snail" style="{snail}" aria-label="Улитка против рыцаря"></button>
    </div>"""


def build_hall(site):
    scene = pixel_scene_html(site)
    lines = []
    for r in site.rooms:
        n = len(site.room_posts[r["id"]])
        lines.append(f'<li><a href="{r["page"]}">{esc(r["name"])}</a><span class="dots"></span>'
                     f'<span class="n">{n} {plural(n, "свиток", "свитка", "свитков")}</span>'
                     f'<span class="d">{esc(r["short"])} · #{esc(r["hashtags"][0])}</span></li>')
    lines.append(f'<li><a href="search.html">Картотека писаря</a><span class="dots"></span>'
                 f'<span class="n">{len(site.posts)} всего</span><span class="d">поиск по всему каналу</span></li>')
    lines.append(f'<li><a href="{esc(site.s["channel_url"])}">Доска у входа</a><span class="dots"></span>'
                 f'<span class="n">↗</span><span class="d">сам канал в Telegram</span></li>')
    latest = site.posts[:6]
    ticker = " ✠ ".join(esc(p["title"]) for p in site.posts[:8])
    latest_html = "".join(f'<li><time datetime="{esc(p["date"])}">{ru_date(p["date"])}</time> '
                          f'<a href="scroll/{p["id"]}.html">{esc(p["title"])}</a></li>' for p in latest)
    body = f"""<section class="hall">
  <h1 class="visually-hidden">{esc(site.s['title'])} — архив канала {esc(site.s['channel_title'])}</h1>
  <div class="scene-frame">
    {scene}
  </div>
  <p class="scene-hint">Наведи свечу на предмет и войди. Или выбери дверь в указателе ниже.</p>
  <div class="ticker" aria-label="Свежие свитки"><div class="ticker-track"><span>Вести с тракта ✠ {ticker} ✠ </span><span aria-hidden="true">Вести с тракта ✠ {ticker} ✠ </span></div></div>
</section>
<div class="hall-grid">
  <section class="parchment welcome">
    <h2>Здравствуй, путник</h2>
    <p class="lead"><span class="dropcap">З</span>десь хранится всё, что утонуло в ленте канала. Telegram течёт, как река: старое уносит, искать неудобно, поисковики туда не заглядывают. А в трактирной книге свитки лежат по полкам.</p>
    <ul class="why">
      <li><b>Поиск.</b> Писарь найдёт любой пост по слову или хэштегу.</li>
      <li><b>Каталоги.</b> Забивки с фильтром «фруктовое, но не приторное», растения с дневником роста, воинства по фракциям, полка с оценками.</li>
      <li><b>Инструменты.</b> Быстрые ярлыки по гайдам про ИИ-агентов.</li>
    </ul>
    <form class="ask" action="search.html" method="get" role="search">
      <label for="ask-q">Спросить писаря</label>
      <div class="ask-row"><input id="ask-q" name="q" type="search" placeholder="что ищешь?"><button class="btn">Искать</button></div>
    </form>
    <h3>Устав трактира</h3>
    <ol class="rules">
      <li>Дым пускать только в дымной горнице.</li>
      <li>Растения не поливать элем, даже если очень просят.</li>
      <li>Оловянных воинов не трогать грязными руками. И чистыми тоже.</li>
      <li>С механическими духами говорить вежливо: они всё запоминают.</li>
      <li>Книги с полки брать можно, возвращать обязательно.</li>
      <li>Улитку не обижать. Она сильнее, чем кажется.</li>
    </ol>
  </section>
  <section class="parchment directory">
    <h2>Указатель</h2>
    <ul class="dir">{''.join(lines)}</ul>
    <h3>Свежие свитки</h3>
    <ul class="latest">{latest_html}</ul>
    <div class="construction"><span class="snail" aria-hidden="true">🐌</span> Трактир ещё строится. Каменщики пьют, улитка наступает.</div>
  </section>
</div>"""
    site.page("index.html", site.s["title"], body, root="", desc=site.s["tagline"], scene=True)


def build_ai(site, r):
    posts = site.room_posts[r["id"]]
    pinned = site.cat.get("ai", {}).get("pinned", [])
    pins = ""
    for it in pinned:
        url = it.get("url") or "#feed"
        pins += (f'<li class="pin">{stamp(it)}<a href="{esc(url)}">{esc(it["title"])}</a>'
                 f'<span>{esc(it.get("note", ""))}</span></li>')
    counts = {}
    for p in posts:
        for t in p["hashtags"]:
            counts[t] = counts.get(t, 0) + 1
    quick = "".join(f'<a class="chip" href="#feed" data-quicktag="{esc(t)}">#{esc(t)} <sup>{n}</sup></a>'
                    for t, n in sorted(counts.items(), key=lambda kv: -kv[1])[:16])
    body = site.room_head(r) + f"""
<section class="parchment quick">
  <h2>Быстрые ярлыки</h2>
  <div class="quick-grid">
    <div><h3>Закреплённые свитки</h3><ul class="pins">{pins or '<li class="empty">Пока ничего не закреплено.</li>'}</ul></div>
    <div><h3>Темы</h3><p class="chips">{quick or '<span class="empty">Тем пока нет.</span>'}</p>
    <p class="tiny">Жми на тему — ниже останутся только нужные свитки.</p></div>
  </div>
</section>
""" + site.feed(posts, "", "Свитки о механических духах", big=True)
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def build_hookah(site, r):
    items = site.cat.get("hookah", {}).get("items", [])
    cards = []
    for it in items:
        mix = "".join(f"<li>{esc(m)}</li>" for m in it.get("mix", []))
        fl = "|".join(it.get("flavors", []))
        link = site.post_link(it.get("post"))
        more = f'<a href="{esc(link)}">читать свиток →</a>' if link else ""
        search = " ".join([it["name"], fl, " ".join(it.get("mix", [])), it.get("note", "")]).lower()
        cards.append(f"""<article class="card recipe entry" data-search="{esc(search)}" data-flavors="{esc(fl)}" data-sweet="{int(it.get('sweetness', 0))}" data-strength="{int(it.get('strength', 0))}" data-rating="{int(it.get('rating', 0))}" data-date="{esc(it.get('date', ''))}" data-name="{esc(it['name'].lower())}">
  {stamp(it)}
  <h3>{esc(it['name'])}</h3>
  <p class="tags">{''.join(f'<span class="chip chip-sm">{esc(f)}</span>' for f in it.get('flavors', []))}</p>
  <ul class="mix">{mix}</ul>
  <dl class="meters">
    <div><dt>Сладость</dt><dd>{pips(it.get('sweetness'), 'sweet', 'Сладость')}</dd></div>
    <div><dt>Крепость</dt><dd>{pips(it.get('strength'), 'strong', 'Крепость')}</dd></div>
    <div><dt>Вердикт</dt><dd>{rating_badge(it.get('rating'))}</dd></div>
  </dl>
  <p class="note">{esc(it.get('note', ''))}</p>
  <p class="meta">{esc(it.get('bowl', ''))}{' · ' if it.get('bowl') else ''}{ru_date(it.get('date', ''))} {more}</p>
</article>""")
    flavors = [f for it in items for f in it.get("flavors", [])]
    body = site.room_head(r) + f"""
<section class="parchment catalog">
  <h2>Книга забивок <small class="count" data-count-for="hookah-list">{len(items)}</small></h2>
  <div class="filterbox" data-target="#hookah-list">
    <label class="search-field"><span>Вкус, табак, слово</span><input type="search" data-search placeholder="малина, мята, чай…"></label>
    {facet_chips(flavors, 'flavors', 'all', 'Вкус:')}
    <div class="row-controls">
      <label class="toggle"><input type="checkbox" data-max="sweet" value="2"> <span>не приторное</span></label>
      <label>Крепость до <select data-max="strength"><option value="">любая</option><option value="2">лёгкая</option><option value="3">средняя</option><option value="4">крепкая</option></select></label>
      <label>Вердикт от <select data-min="rating"><option value="">любой</option><option value="3">сносно</option><option value="4">добро</option><option value="5">благодать</option></select></label>
      <label>Порядок <select data-sort><option value="rating-desc">лучшие</option><option value="date-desc">новые</option><option value="sweet-asc">несладкие</option><option value="name-asc">по имени</option></select></label>
      <button type="button" class="btn-link" data-reset>сбросить</button>
    </div>
  </div>
  <div class="cards cards-3" id="hookah-list">{''.join(cards)}</div>
  <p class="nothing" hidden>Такой забивки в книге нет. Может, изобретёшь?</p>
</section>
""" + site.feed(site.room_posts[r["id"]], "", "Свитки из дымной горницы")
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


STATUS_CLASS = {"растёт": "ok", "цветёт": "bloom", "плодоносит": "fruit", "спит": "sleep", "почило": "dead",
                "покрашено": "ok", "в процессе": "wip", "грунт": "sleep", "куча позора": "dead",
                "прочитано": "ok", "брошено": "dead", "в планах": "sleep"}


def diary_entry(site, d):
    pic = f'<img src="{esc(d["photo"])}" alt="" loading="lazy">' if d.get("photo") else ""
    link = site.post_link(d.get("post"))
    more = f' <a href="{esc(link)}">свиток →</a>' if link else ""
    return f'<li><time datetime="{esc(d["date"])}">{ru_date(d["date"])}</time>{pic}<p>{esc(d["text"])}{more}</p></li>'


def build_garden(site, r):
    items = site.cat.get("garden", {}).get("items", [])
    cards = []
    for it in items:
        days = (site.today - dt.date.fromisoformat(it["since"])).days if it.get("since") else None
        diary = "".join(diary_entry(site, d) for d in it.get("diary", []))
        care = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in it.get("care", {}).items())
        pic = f'<img src="{esc(it["photo"])}" alt="{esc(it["name"])}" loading="lazy">' if it.get("photo") else '<img class="pix" src="assets/scene/icon-garden.png" alt="">'
        st = it.get("status", "")
        search = " ".join([it["name"], it.get("latin", ""), st, it.get("place", "")] + [d["text"] for d in it.get("diary", [])]).lower()
        cards.append(f"""<article class="card plant entry" data-search="{esc(search)}" data-status="{esc(st)}" data-date="{esc(it.get('since', ''))}" data-name="{esc(it['name'].lower())}">
  {stamp(it)}
  <div class="plant-top">
    <div class="plant-pic">{pic}</div>
    <div>
      <h3>{esc(it['name'])}</h3>
      <p class="latin">{esc(it.get('latin', ''))}</p>
      <p><span class="status s-{STATUS_CLASS.get(st, 'ok')}">{esc(st)}</span></p>
      <p class="meta">{'в трактире с ' + ru_date(it['since']) if it.get('since') else ''}{f' · {days} {plural(days, "день", "дня", "дней")}' if days is not None else ''}{' · ' + esc(it['place']) if it.get('place') else ''}</p>
    </div>
  </div>
  <dl class="care">{care}</dl>
  <details class="diary" open><summary>Дневник роста ({len(it.get('diary', []))})</summary><ol class="timeline">{diary}</ol></details>
</article>""")
    body = site.room_head(r) + f"""
<section class="parchment catalog">
  <h2>Грядки и горшки <small class="count" data-count-for="garden-list">{len(items)}</small></h2>
  <div class="filterbox" data-target="#garden-list">
    <label class="search-field"><span>Растение или запись</span><input type="search" data-search placeholder="перец, пересадка, тля…"></label>
    {facet_chips([it.get('status', '') for it in items], 'status', 'any', 'Состояние:')}
    <div class="row-controls"><label>Порядок <select data-sort><option value="date-desc">новые</option><option value="date-asc">старожилы</option><option value="name-asc">по имени</option></select></label><button type="button" class="btn-link" data-reset>сбросить</button></div>
  </div>
  <div class="cards cards-2" id="garden-list">{''.join(cards)}</div>
  <p class="nothing" hidden>Такое здесь не растёт.</p>
</section>
""" + site.feed(site.room_posts[r["id"]], "", "Свитки с огорода")
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def mini_placeholder(color):
    return f'<div class="mini-ph" style="--fc:{esc(color)}"><img class="pix" src="assets/scene/icon-soldier.png" alt=""></div>'


def build_minis(site, r):
    data = site.cat.get("minis", {})
    factions = {f["id"]: f for f in data.get("factions", [])}
    items = data.get("items", [])
    cards = []
    for it in items:
        f = factions.get(it.get("faction"), {"name": it.get("faction", "?"), "color": "#777"})
        pic = (f'<a class="zoom" href="{esc(it["photo"])}"><img src="{esc(it["photo"])}" alt="{esc(it["name"])}" loading="lazy"></a>'
               if it.get("photo") else mini_placeholder(f["color"]))
        link = site.post_link(it.get("post"))
        st = it.get("status", "")
        search = " ".join([it["name"], f["name"], st, it.get("note", "")]).lower()
        cards.append(f"""<figure class="card mini entry" style="--fc:{esc(f['color'])}" data-search="{esc(search)}" data-faction="{esc(f['name'])}" data-status="{esc(st)}" data-date="{esc(it.get('date', ''))}" data-name="{esc(it['name'].lower())}">
  {stamp(it)}
  <div class="mini-pic">{pic}</div>
  <figcaption><b>{esc(it['name'])}</b><span class="banner">{esc(f['name'])}</span>
  <span class="status s-{STATUS_CLASS.get(st, 'ok')}">{esc(st)}</span>
  <small>{esc(it.get('note', ''))}</small>
  <small class="meta">{ru_date(it.get('date', ''))}{f' · <a href="{esc(link)}">свиток →</a>' if link else ''}</small></figcaption>
</figure>""")
    legend = ""
    for f in factions.values():
        n = sum(1 for it in items if it.get("faction") == f["id"])
        done = sum(1 for it in items if it.get("faction") == f["id"] and it.get("status") == "покрашено")
        legend += (f'<li style="--fc:{esc(f["color"])}"><span class="flag"></span><b>{esc(f["name"])}</b>'
                   f'<small>{esc(f.get("system", ""))} · «{esc(f.get("motto", ""))}»</small>'
                   f'<span class="n">{done}/{n} покрашено</span></li>')
    shame = sum(1 for it in items if it.get("status") != "покрашено")
    body = site.room_head(r) + f"""
<section class="parchment catalog">
  <h2>Воинства <small class="count" data-count-for="minis-list">{len(items)}</small></h2>
  <ul class="factions">{legend}</ul>
  <p class="shame">Некрашеного в куче позора: <b>{shame}</b>. Летописец скорбит.</p>
  <div class="filterbox" data-target="#minis-list">
    {facet_chips([factions.get(it.get('faction'), {}).get('name', it.get('faction', '')) for it in items], 'faction', 'any', 'Фракция:')}
    {facet_chips([it.get('status', '') for it in items], 'status', 'any', 'Готовность:')}
    <div class="row-controls"><label class="search-field inline"><span>Поиск</span><input type="search" data-search placeholder="сержант, ржавчина…"></label><label>Порядок <select data-sort><option value="date-desc">новые</option><option value="date-asc">старые</option><option value="name-asc">по имени</option></select></label><button type="button" class="btn-link" data-reset>сбросить</button></div>
  </div>
  <div class="cards gallery" id="minis-list">{''.join(cards)}</div>
  <p class="nothing" hidden>Таких воинов не нашлось. Может, они ещё в коробке.</p>
</section>
""" + site.feed(site.room_posts[r["id"]], "", "Свитки из оружейной")
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def build_shelf(site, r):
    items = site.cat.get("shelf", {}).get("items", [])
    cards = []
    for it in items:
        link = site.post_link(it.get("post"))
        t = it.get("type", "книга")
        hue = sum(map(ord, it["title"])) % 360
        search = " ".join([it["title"], it.get("author", ""), t, " ".join(it.get("genres", [])), it.get("verdict", "")]).lower()
        cards.append(f"""<article class="card book entry" style="--h:{hue}" data-search="{esc(search)}" data-type="{esc(t)}" data-status="{esc(it.get('status', ''))}" data-rating="{int(it.get('rating', 0))}" data-name="{esc(it['title'].lower())}" data-date="{esc(it.get('date', ''))}">
  {stamp(it)}
  <div class="spine" aria-hidden="true"><span>{esc(it['title'])}</span></div>
  <div class="book-body">
    <p class="type">{esc(t)}</p>
    <h3>{esc(it['title'])}</h3>
    <p class="author">{esc(it.get('author', ''))}</p>
    <p>{rating_badge(it.get('rating'))}</p>
    <p class="verdict">«{esc(it.get('verdict', ''))}»</p>
    <p class="meta"><span class="status s-{STATUS_CLASS.get(it.get('status', ''), 'ok')}">{esc(it.get('status', ''))}</span> {' · '.join(esc(g) for g in it.get('genres', []))}{f' · <a href="{esc(link)}">свиток →</a>' if link else ''}</p>
  </div>
</article>""")
    body = site.room_head(r) + f"""
<section class="parchment catalog">
  <h2>На полке <small class="count" data-count-for="shelf-list">{len(items)}</small></h2>
  <div class="filterbox" data-target="#shelf-list">
    <label class="search-field"><span>Название, автор, жанр</span><input type="search" data-search placeholder="Берсерк, Эко, фэнтези…"></label>
    {facet_chips([it.get('type', '') for it in items], 'type', 'any', 'Что:')}
    {facet_chips([it.get('status', '') for it in items], 'status', 'any', 'Статус:')}
    <div class="row-controls"><label>Оценка от <select data-min="rating"><option value="">любая</option><option value="3">сносно</option><option value="4">добро</option><option value="5">благодать</option></select></label><label>Порядок <select data-sort><option value="rating-desc">лучшие</option><option value="name-asc">по имени</option></select></label><button type="button" class="btn-link" data-reset>сбросить</button></div>
  </div>
  <div class="cards cards-2" id="shelf-list">{''.join(cards)}</div>
  <p class="nothing" hidden>Такого на полке нет. Пока.</p>
</section>
""" + site.feed(site.room_posts[r["id"]], "", "Свитки с полки")
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def build_search(site):
    index = [{"id": p["id"], "t": p["title"], "x": p["excerpt"], "s": p["search"][:4000], "h": p["hashtags"],
              "d": p["date"][:10], "r": p["rooms"], "i": p["photos"][0] if p["photos"] else ""} for p in site.posts]
    (SITE / "assets" / "search-index.js").write_text(
        "window.TAVERN_INDEX=" + json.dumps(index, ensure_ascii=False, separators=(",", ":")) + ";\n"
        "window.TAVERN_ROOMS=" + json.dumps({r["id"]: r["name"] for r in site.rooms}, ensure_ascii=False) + ";\n",
        encoding="utf-8")
    counts = {}
    for p in site.posts:
        for t in p["hashtags"]:
            counts[t] = counts.get(t, 0) + 1
    chips = "".join(f'<button type="button" class="chip" data-tag="{esc(t)}">#{esc(t)} <sup>{n}</sup></button>'
                    for t, n in sorted(counts.items(), key=lambda kv: -kv[1])[:60])
    opts = "".join(f'<option value="{r["id"]}">{esc(r["name"])}</option>' for r in site.rooms)
    body = f"""<section class="room-head">
  <div class="marginalia" aria-hidden="true"><img class="pix" src="assets/scene/icon-search.png" alt=""></div>
  <div><p class="crumbs"><a href="index.html">Общий зал</a> › Картотека писаря</p>
  <h1>Картотека писаря</h1>
  <p class="epigraph">Спроси — и писарь, ворча, пороется в сундуках.</p>
  <p class="about">Поиск по всем {len(site.posts)} свиткам канала: по словам, хэштегам и комнатам.</p></div>
</section>
<section class="parchment" id="search-app">
  <form class="ask" role="search" onsubmit="return false">
    <div class="ask-row"><input id="q" type="search" placeholder="слово, имя, вкус…" autocomplete="off" aria-label="Что искать"><select id="room" aria-label="Комната"><option value="">все комнаты</option>{opts}</select></div>
  </form>
  <div class="chips" id="tagchips">{chips}</div>
  <p class="result-count" id="rc" aria-live="polite"></p>
  <ol class="results" id="results"></ol>
  <noscript><p>Писарь без JavaScript не ищет, но все свитки есть в комнатах трактира.</p></noscript>
</section>
<script src="assets/search-index.js"></script>"""
    site.page("search.html", "Картотека писаря", body, room="search", desc="Поиск по всем постам канала")


def build_scrolls(site):
    target = SITE / "scroll"
    for old in target.glob("*.html"):
        old.unlink()
    room_by_id = {r["id"]: r for r in site.rooms}
    for p in site.posts:
        root = "../"
        room = room_by_id.get(p["rooms"][0]) if p["rooms"] else None
        crumbs = f'<a href="../index.html">Общий зал</a> › '
        crumbs += (f'<a href="../{room["page"]}">{esc(room["name"])}</a>' if room
                   else '<a href="../search.html">Картотека</a>')
        pics = "".join(f'<a class="zoom" href="{root}{esc(ph)}"><img src="{root}{esc(ph)}" alt="" loading="lazy"></a>' for ph in p["photos"])
        tags = "".join(f'<a class="chip" href="{root}search.html?tag={esc(t)}">#{esc(t)}</a>' for t in p["hashtags"])
        tg = site.tg_link(p["id"])
        siblings = site.room_posts[room["id"]] if room else site.posts
        i = siblings.index(p)
        newer = siblings[i - 1] if i > 0 else None
        older = siblings[i + 1] if i + 1 < len(siblings) else None
        nav = ""
        if older:
            nav += f'<a class="prev" href="{older["id"]}.html">← {esc(older["title"])}</a>'
        if newer:
            nav += f'<a class="next" href="{newer["id"]}.html">{esc(newer["title"])} →</a>'
        body = f"""<article class="parchment scroll-page">
  <p class="crumbs">{crumbs}</p>
  {'<span class="stamp">образец</span>' if p.get('sample') else ''}
  <h1>{esc(p['title'])}</h1>
  <p class="meta"><time datetime="{esc(p['date'])}">{ru_date(p['date'])}</time> · свиток №{p['id']}</p>
  {f'<div class="scroll-pics n{min(len(p["photos"]), 3)}">{pics}</div>' if pics else ''}
  <div class="scroll-body">{render_entities(p['entities'], root, p['_cut'], p['_end'])}</div>
  <p class="tags">{tags}</p>
  <p class="actions">{f'<a class="btn" href="{esc(tg)}" rel="noopener" target="_blank">Обсудить в канале ↗</a>' if tg else ''} <a class="btn btn-ghost" href="../{room['page'] if room else 'search.html'}">Назад в комнату</a></p>
  <nav class="scroll-nav" aria-label="Соседние свитки">{nav}</nav>
</article>"""
        site.page(f"scroll/{p['id']}.html", p["title"], body, root=root, room=room["id"] if room else None,
                  desc=p["excerpt"][:200])


def build_sitemap(site):
    base = site.s["base_url"]
    urls = [base] + [base + r["page"] for r in site.rooms] + [base + "search.html"]
    urls += [f"{base}scroll/{p['id']}.html" for p in site.posts]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n"
    (SITE / "sitemap.xml").write_text(xml, encoding="utf-8")


BUILDERS = {"ai": build_ai, "hookah": build_hookah, "garden": build_garden, "minis": build_minis, "shelf": build_shelf}


def main():
    ap = argparse.ArgumentParser(description="Собрать Трактирную книгу")
    ap.add_argument("--export", help="папка экспорта Telegram (ChatExport_…)")
    ap.add_argument("--no-media", action="store_true", help="не копировать картинки из экспорта")
    args = ap.parse_args()

    if args.export:
        run_import(args.export, args.no_media)

    cfg = load_json(SRC / "config.json")
    catalogs = {p.stem: load_json(p) for p in (SRC / "catalog").glob("*.json")}
    posts = enrich(load_posts(), cfg["rooms"])
    site = Site(cfg, posts, catalogs)

    build_hall(site)
    for r in site.rooms:
        BUILDERS.get(r["id"], build_ai)(site, r)
    build_search(site)
    build_scrolls(site)
    build_sitemap(site)

    known = {t.lower() for r in cfg["rooms"] for t in r["hashtags"]}
    stray = {}
    for p in posts:
        for t in p["hashtags"]:
            if t not in known:
                stray[t] = stray.get(t, 0) + 1
    print(f"Готово: {len(posts)} свитков, комнаты: " +
          ", ".join(f"{r['short']} {len(site.room_posts[r['id']])}" for r in cfg["rooms"]))
    homeless = sum(1 for p in posts if not p["rooms"])
    if homeless:
        print(f"Без комнаты (только в поиске): {homeless}")
    if stray:
        top = sorted(stray.items(), key=lambda kv: -kv[1])[:30]
        print("Хэштеги, не привязанные к комнатам (добавьте нужные в config.json):")
        print("  " + ", ".join(f"#{t} ({n})" for t, n in top))


if __name__ == "__main__":
    main()
