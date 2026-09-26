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
  _src/catalog/heroes.json — герои таверны и её мир (страница «Кто в таверне», смотрители комнат)
  _src/pixel_scene.py     — рисует пиксельный зал (assets/scene/*, hotspots.json)
  _src/pixel_heroes.py    — пиксельные портреты героев и неоновые текстуры (assets/heroes/*)
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
HASHTAG_RE = re.compile(r"#([0-9A-Za-zА-Яа-яЁё_]+)")
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
# цвета комнат: подсветка ссылок, «зеркала» на орбите (совпадают с ORBS в pixel_heroes.py)
ROOM_COLOR = {"shelf": "#ff5fa8", "garden": "#b6ff5a", "hookah": "#ffb05a", "ai": "#6ff0ff", "games": "#c89bff",
              "minis": "#ffe66a", "anime": "#ff7ae0", "thoughts": "#ffd259", "search": "#e6ff3a"}

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
    posts = [p for p in posts if p["_has_text"] or p["photos"]]
    for p in posts:
        p.pop("_has_text", None)
        p.pop("ts", None)
    print(f"  в архив попало постов: {len(posts)}")
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


GREETING_RE = re.compile(
    r"^\W*(ну\s+)?(здоро'?в|здорво|всем|всех|привет|хай|hola|добр|проснулись|вечер|утро|пятниц|щитверг|"
    r"сегодня\s+среда|это\s+среда|часик|коллеги|кто\s+прочитал|всм|гудморнинг|поднять\s+мечи|"
    r"ну\s+что|ловите|солнышки|дружочки|it's)", re.I)
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")


TAG_WORD_RE = re.compile(r"#([0-9A-Za-zА-Яа-яЁё_]+)(@\w+)?")
SHORT_WORDS = {"под", "про", "по", "в", "во", "о", "об", "для", "с", "со", "к", "на", "и", "тег", "тегу"}


def title_clean(line):
    """Строка для заголовка: хвост из хэштегов убираем (если он не часть фразы), остальные — словом."""
    head = re.sub(r"(\s*#[^\s#]+)+\s*$", "", line)
    tail = line[len(head):].split()
    if tail and head.split() and head.split()[-1].lower() in SHORT_WORDS:
        head = head + " " + tail[0]
    head = TAG_WORD_RE.sub(r"\1", head)
    return re.sub(r"\s+", " ", head).strip(" \t—-–:|•·")


def text_clean(line):
    """Строка для анонса: строки из одних хэштегов выкидываем, в остальных хэштеги становятся словами."""
    if not strip_tags_line(line):
        return ""
    return re.sub(r"\s+", " ", TAG_WORD_RE.sub(r"\1", line)).strip()


def pick_title(text):
    """Заголовок свитка: первая содержательная строка, не приветствие.
    Возвращает (заголовок, сколько символов срезать с начала текста)."""
    offset, first_line, fallback = 0, True, ""
    for line in text.split("\n"):
        start = offset
        offset += len(line) + 1
        clean = title_clean(line)
        if not clean or not re.search(r"[A-Za-zА-Яа-яЁё]{3}", clean):
            if clean:
                first_line = False
            continue
        if GREETING_RE.match(clean) and len(clean) < 70:
            fallback = fallback or clean
            first_line = False
            continue
        title = SENTENCE_RE.split(clean, 1)[0]
        if len(title) < 12:
            title = clean
        whole = title == clean
        if len(title) > 100:
            title, whole = title[:92].rsplit(" ", 1)[0].rstrip(",;:—- ") + "…", False
        return title, (offset if whole and first_line and start == 0 else 0)
    return fallback, 0


def enrich(posts, rooms):
    tag_to_rooms = {}
    for r in rooms:
        for t in r["hashtags"]:
            tag_to_rooms.setdefault(t.lower(), []).append(r["id"])
    for p in posts:
        text = "".join(e["text"] for e in p["entities"])
        p["text"] = text
        p["hashtags"] = list(dict.fromkeys(t.lower() for t in HASHTAG_RE.findall(text)
                                           if not re.fullmatch(r"[0-9a-fA-F]{6}", t)))  # #24f000 — это цвет
        p["rooms"] = list(dict.fromkeys(rid for t in p["hashtags"] for rid in tag_to_rooms.get(t, [])))
        title, cut = pick_title(text)
        if not title:
            title = "Свиток без слов" if p["photos"] else "Пустой свиток"
        p["title"] = title
        p["_cut"] = cut
        body = text.rstrip()
        while body and "#" in body.rsplit("\n", 1)[-1] and not strip_tags_line(body.rsplit("\n", 1)[-1]):
            body = body.rsplit("\n", 1)[0].rstrip() if "\n" in body else ""
        p["_end"] = max(len(body), cut)
        plain = re.sub(r"\s+", " ", " ".join(text_clean(l) for l in text.split("\n"))).strip()
        at = plain.find(title.rstrip("…"))
        rest = plain[at + len(title.rstrip("…")):] if at >= 0 else plain
        rest = rest.lstrip(" .!?…—-–:")
        p["excerpt"] = rest if len(rest) <= 240 else rest[:230].rsplit(" ", 1)[0] + "…"
        if re.fullmatch(r"Выпуск №\s?\d+", title) and "выдыхай" in p["hashtags"]:
            p["title"] = title = "«Выдыхай», " + title.lower()
            if len(p["excerpt"]) < 25:
                p["excerpt"] = "Аудиовыпуск пятничного подкаста — слушать в канале. " + p["excerpt"].replace("Выдыхай", "").strip(" -—")
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
            tag = s.lstrip("#").split("@")[0].lower()
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
        self.hero_data = catalogs.get("heroes") or {}
        self.heroes = self.hero_data.get("heroes", [])
        self.quotes = [f"«{a}» — {b}" if b else f"«{a}…»" for a, b in self.hero_data.get("guestbook", [])] or [
            "Плата — одна забытая вещь. Сдача не даётся."]

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
        nav = ""
        for r in self.rooms:
            day = f'<small>{esc(r["day"])}</small>' if r.get("day") else ""
            nav += (f'<a class="tn{" is-here" if room == r["id"] else ""}" href="{root}{r["page"]}" style="--rc:{ROOM_COLOR.get(r["id"], "#e6ff3a")}">'
                    f'<img src="{root}assets/heroes/{self.keeper_of(r["id"])["id"]}.png" alt="" width="16" height="16">'
                    f'<span>{esc(r["sign"])}</span>{day}</a>')
        nav += (f'<a class="tn tn-search{" is-here" if room == "search" else ""}" href="{root}search.html" style="--rc:{ROOM_COLOR["search"]}">'
                f'<img src="{root}assets/heroes/osevoy.png" alt="" width="16" height="16"><span>Картотека</span></a>'
                f'<a class="tn tn-guests{" is-here" if room == "guests" else ""}" href="{root}guests.html" style="--rc:#ff6a1f">'
                f'<img src="{root}assets/heroes/lisivy.png" alt="" width="16" height="16"><span>Кто здесь</span></a>')
        metrika = ""
        if s.get("yandex_metrika"):
            mid = int(s["yandex_metrika"])
            metrika = f"""<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();for(var j=0;j<document.scripts.length;j++){{if(document.scripts[j].src===r){{return;}}}}k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,'script','https://mc.yandex.ru/metrika/tag.js?id={mid}','ym');ym({mid},'init',{{ssr:true,clickmap:true,trackLinks:true,accurateTrackBounce:true}});</script>"""
        neighbors = "".join(f'<a href="{esc(n["url"])}">{esc(n["title"])}</a>' for n in s.get("neighbors", []))
        chan = esc(s["channel_url"])
        sample_note = ('<div class="sample-bar">Таверна обставлена <b>образцами</b>: '
                       'настоящие посты появятся после импорта экспорта канала.</div>') if self.sample else ""
        canonical = s["base_url"] + (path if path != "index.html" else "")
        first = ru_date(self.posts[-1]["date"]) if self.posts else "—"
        last = ru_date(self.posts[0]["date"]) if self.posts else "—"
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
<meta name="theme-color" content="#050706">
<link rel="icon" href="{root}assets/favicon.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600&family=JetBrains+Mono:ital,wght@0,400;0,700;1,400&family=Press+Start+2P&family=Rubik+Glitch&family=Unbounded:wght@600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/tavern.css">
<script>try{{if(localStorage.getItem("tavern-still")==="1")document.documentElement.classList.add("is-still")}}catch(e){{}}</script>
{metrika}
</head>
<body class="{'is-hall' if scene else 'is-room'}{' room-' + room if room else ''}">
<a class="skip" href="#main">К содержимому</a>
<header class="topbar">
  <a class="logo" href="{root}index.html" title="В общий зал"><img src="{root}assets/heroes/kalyanych.png" alt="" width="24" height="24"><span>лисья<b>.</b>таверна</span></a>
  <nav class="topnav" aria-label="Комнаты таверны">{nav}</nav>
  <button type="button" class="still-btn" aria-pressed="false" title="Остановить движение на странице"><span aria-hidden="true">⏸</span><span class="visually-hidden">Остановить движение</span></button>
</header>
{sample_note}
<main id="main">
{body}
</main>
<footer class="bottom">
  <p class="statbar"><span>свитков: <b>{len(self.posts)}</b></span><span>комнат: <b>{len(self.rooms)}</b></span><span>первый свиток: <b>{first}</b></span><span>последний: <b>{last}</b></span><span>плата: <b>одна забытая вещь</b></span></p>
  <div class="foot-grid">
    <section class="panel box">
      <h3 class="bar">Грамота</h3>
      <div class="box-in">
        <p>Архив канала <a href="{chan}">{esc(s['channel_title'])}</a>. Лента в Telegram течёт и тонет, а здесь всё лежит по полкам, подписанное Дедом Осевым.</p>
        <p>Стучаться к хозяину: <a href="{esc(s.get('owner_url', chan))}">{esc(s.get('owner', ''))}</a></p>
        <p class="quote" data-quotes='{esc(json.dumps(self.quotes, ensure_ascii=False))}'>{esc(self.quotes[0])}</p>
      </div>
    </section>
    <section class="panel box">
      <h3 class="bar">Банки в подвале</h3>
      <div class="box-in">
        <p class="candles" aria-live="polite"><span class="candle-row" aria-hidden="true"></span><span class="candle-text">Ты здесь впервые. Плата — одна забытая вещь.</span></p>
        <p class="tiny">Банки считаются только в твоём браузере. Хозяин ищет в них своё имя, а не твоё.</p>
      </div>
    </section>
    <section class="panel box">
      <h3 class="bar">Трактовое кольцо</h3>
      <div class="box-in">
        <p class="ring">{neighbors}<a href="{chan}">Канал в Telegram</a><a href="{root}guests.html">Кто в таверне</a><a href="{root}sitemap.xml">Карта таверны</a></p>
        <div class="buttons88" aria-hidden="true">
          <span class="b88 b-a">смотреть<br>при жаровне</span>
          <span class="b88 b-b">восьмое<br>зеркало</span>
          <span class="b88 b-c">бобылей<br>не выдаём</span>
          <span class="b88 b-d">осам<br>не наливаем</span>
        </div>
      </div>
    </section>
  </div>
  <p class="colophon">Подписано Дедом Осевым, {self.today.year} · <a href="{root}index.html">общий зал</a> · <a href="#main">наверх ↑</a></p>
</footer>
<script src="{root}assets/tavern.js"></script>
</body>
</html>
"""
        out = SITE / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html_out, encoding="utf-8")

    def keeper_of(self, room_id):
        """Кто из героев присматривает за комнатой (поле room/rooms в catalog/heroes.json)."""
        for h in self.heroes:
            if room_id == h.get("room") or room_id in h.get("rooms", []):
                return h
        return self.heroes[0] if self.heroes else {"id": "kalyanych", "name": "Лис Кальяныч", "quote": ""}

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
            return f'<section class="parchment"><h2>{esc(title)}</h2><p class="empty">{esc(empty or "Свиток пуст. Томик ещё не дочитал — с конца это долго.")}</p></section>'
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

    def room_head(self, r, count=None, root=""):
        """Шапка комнаты: смотритель в зеркале и «инспектор» с выносками, как на espy.world."""
        n = len(self.room_posts[r["id"]]) if count is None else count
        tags = " ".join(f"#{t}" for t in r.get("hashtags", [])[:4])
        k = self.keeper_of(r["id"])
        color = ROOM_COLOR.get(r["id"], "#e6ff3a")
        day = DAYS.get(r.get("day", ""), "в любой день") if r.get("hashtags") else "всегда"
        rows = [("смотритель", f'<a href="{root}guests.html#{esc(k["id"])}">{esc(k["name"])}</a>'),
                ("когда", esc(day)),
                ("свитков", f'{n} {plural(n, "свиток", "свитка", "свитков")}' if r.get("hashtags") else f"{n} всего")]
        if tags:
            rows.append(("метки", f'<span class="mono">{esc(tags)}</span>'))
        rows_html = "".join(f'<div class="irow"><span class="ik">{a}</span><span class="iv">{b}</span></div>' for a, b in rows)
        return f"""<section class="room-head" style="--rc:{color}">
  <div class="rh-mirror" aria-hidden="true">
    <img class="rh-orb" src="{root}assets/heroes/orb-{esc(r['id'] if r['id'] in ROOM_COLOR else 'search')}.png" alt="">
    <img class="rh-keeper" src="{root}assets/heroes/{esc(k['id'])}.png" alt="">
  </div>
  <div class="rh-text">
    <p class="crumbs"><a href="{root}index.html">общий зал</a> <span>›</span> {esc(r['name'])}</p>
    <h1>{esc(r['name'])}</h1>
    <p class="epigraph">{esc(r['epigraph'])}</p>
    <p class="about">{esc(r['about'])}</p>
    <div class="inspect rh-rows">{rows_html}</div>
    <p class="keeper-says"><img src="{root}assets/heroes/{esc(k['id'])}.png" alt="" width="32" height="32"><span>«{esc(k.get('quote', ''))}» <small>— {esc(k['name'])}</small></span></p>
  </div>
</section>"""


DAYS = {"Пн": "по понедельникам", "Вт": "по вторникам", "Ср": "по средам", "Чт": "по четвергам",
        "Пт": "по пятницам", "Сб": "по субботам", "Вс": "по воскресеньям"}


def plural(n, one, few, many):
    n = abs(n) % 100
    if 10 < n < 20:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


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
    order = ["search", "garden", "shelf", "thoughts", "ai", "anime", "minis", "games", "hookah"]  # поздние — поверх
    hls, links = [], []
    for key in order:
        if key not in spots["hot"]:
            continue
        x0, y0, x1, y1 = spots["hot"][key]
        if key in rooms:
            r = rooms[key]
            href, name, n = r["page"], r["sign"], len(site.room_posts[key])
            aria = f'{r["name"]}: {n} {plural(n, "свиток", "свитка", "свитков")}'
        elif key == "search":
            href, name, n = "search.html", "Картотека", len(site.posts)
            aria = f"Доска Деда Осевого: поиск по {n} свиткам"
        else:
            continue
        style = (f"left:{x0 / sw * 100:.3f}%;top:{y0 / sh * 100:.3f}%;"
                 f"width:{(x1 - x0) / sw * 100:.3f}%;height:{(y1 - y0) / sh * 100:.3f}%")
        count = f" <b>{n}</b>" if n is not None else " <b>↗</b>"
        hls.append(f'<img class="pix-hl" data-hl="{key}" src="assets/scene/hl-{key}.png" alt="">')
        links.append(f'<a class="pix-hot" data-room="{key}" href="{esc(href)}" style="{style}" aria-label="{esc(aria)}">'
                     f'<span class="pix-label">{esc(name)}{count}</span></a>')
    snail = (f"left:{300 / sw * 100:.3f}%;top:{256 / sh * 100:.3f}%;"
             f"width:{56 / sw * 100:.3f}%;height:{22 / sh * 100:.3f}%")
    return f"""<div class="pix-scene" role="group" aria-label="Общий зал Лисьей таверны: окно с огородом, книжная полка, очаг, доска Деда Осевого, стол с гаданием и грибом Гаврилычем, зеркало с лисом, шкаф с оловянным полком Плюмбия, бочка с костями, Герой Шутливый Лисивый с бидоном, бобыль и Лис Кальяныч с кальяном">
      <div class="pix-film" aria-hidden="true"><img src="assets/scene/frames.png" alt="" width="{sw * 4}" height="{sh}"></div>
      {''.join(hls)}
      {''.join(links)}
      <button type="button" class="pix-snail" style="{snail}" aria-label="Бобыль из-под пола"></button>
    </div>"""


def fox_figure_svg():
    """Лис Кальяныч во весь рост: неоновый контур, как демон-машина на espy.world.
    Голова — лого таверны (xml-agr.ru/lisya-taverna.html), тело дорисовано по описанию:
    стёганка цвета старой хвои, фартук из клеёнки, связка мундштуков, тлеющий хвост и чаша."""
    beads = []
    for i in range(1, 10):
        t = i / 10
        x = (1 - t) ** 2 * 148 + 2 * (1 - t) * t * 210 + t ** 2 * 272
        y = (1 - t) ** 2 * 258 + 2 * (1 - t) * t * 326 + t ** 2 * 258
        col = "#ffd259" if i % 2 else "#d49f3e"
        beads.append(f'<rect x="{x - 2.5:.1f}" y="{y - 2:.1f}" width="5" height="13" rx="2" fill="{col}"/>')
    head = """<polygon points="37,16 68,70 28,74" fill="#8d3b16"/>
      <polygon points="43,29 64,68 47,68" fill="#3a1a10"/>
      <polygon points="163,16 172,74 132,70" fill="#a8471a"/>
      <polygon points="157,29 169,70 153,68" fill="#3a1a10"/>
      <polygon points="100,52 62,73 100,112" fill="#c4551f"/>
      <polygon points="100,52 138,73 100,112" fill="#a8471a"/>
      <polygon points="62,73 71,115 100,112" fill="#e07a3a"/>
      <polygon points="138,73 129,115 100,112" fill="#b64d1c"/>
      <polygon points="28,74 68,70 71,115" fill="#8d3b16"/>
      <polygon points="172,74 132,70 129,115" fill="#7d3413"/>
      <polygon points="76,90 95,86 87,101" fill="#140f0b"/>
      <polygon points="124,90 105,86 113,101" fill="#140f0b"/>
      <polygon class="eye" points="79,89 88,88 85,93" fill="#6fc9bd"/>
      <polygon class="eye" points="121,89 112,88 115,93" fill="#6fc9bd"/>
      <polygon points="71,115 100,112 84,142" fill="#d9dbc6"/>
      <polygon points="129,115 100,112 116,142" fill="#bcbfa9"/>
      <polygon points="84,142 100,112 116,142" fill="#e8dcc6"/>
      <polygon points="84,142 116,142 100,172" fill="#cfd1bb"/>
      <polygon points="90,152 110,152 100,168" fill="#140f0b"/>
      <polygon points="116,150 168,178 164,190 112,160" fill="#3d3226"/>
      <polygon points="164,186 178,180 176,196" fill="#2a231b"/>
      <polygon class="ember" points="172,183 182,180 180,192" fill="#e2662a"/>"""
    return f"""<svg class="fox-svg" viewBox="-60 0 580 780" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <pattern id="quilt" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="16" height="16" fill="#0b150e"/>
      <path d="M0 0H16M0 0V16" stroke="#2f5a38" stroke-width="1.4"/>
      <circle cx="8" cy="8" r="1.2" fill="#46654b"/>
    </pattern>
    <pattern id="oilcloth" width="14" height="14" patternUnits="userSpaceOnUse">
      <rect width="14" height="14" fill="#0a1616"/>
      <rect width="7" height="7" fill="#123030"/>
      <rect x="7" y="7" width="7" height="7" fill="#123030"/>
    </pattern>
    <radialGradient id="flask" cx=".4" cy=".35" r=".7">
      <stop offset="0" stop-color="#6ff0ff" stop-opacity=".55"/>
      <stop offset="1" stop-color="#0a1a2a" stop-opacity=".9"/>
    </radialGradient>
  </defs>
  <!-- хвост: кончик тлеет, от него раскуривают уголь -->
  <path class="tail" d="M74,704 C4,700 -48,600 -40,480 C-38,446 -22,420 2,426 C-10,470 -6,560 66,612 Z" fill="#c4551f"/>
  <path d="M-40,480 C-38,446 -22,420 2,426 C-6,446 -24,470 -40,480 Z" fill="#e8dcc6"/>
  <circle class="ember tip" cx="-8" cy="428" r="7" fill="#ff6a1f"/>
  <g class="wisps"><path d="M-8,414 c-10,-18 12,-30 0,-52 c-8,-16 10,-26 4,-44"/><path d="M0,418 c8,-20 -10,-34 4,-56"/></g>
  <!-- стёганка -->
  <path class="robe" d="M150,240 L270,240 L330,290 L352,420 L362,760 L58,760 L68,420 L90,290 Z" fill="url(#quilt)"/>
  <path class="arm" d="M92,292 C48,380 50,470 104,528" fill="none"/>
  <path class="arm" d="M328,292 C372,360 372,430 334,470" fill="none"/>
  <!-- фартук из клеёнки -->
  <path class="apron" d="M160,300 L260,300 L278,760 L142,760 Z" fill="url(#oilcloth)"/>
  <path class="strap" d="M160,300 L182,252 M260,300 L238,252"/>
  <!-- чаша: кальян -->
  <ellipse class="brass" cx="430" cy="752" rx="42" ry="8" fill="#1c120b"/>
  <circle class="glass" cx="430" cy="700" r="46" fill="url(#flask)"/>
  <g class="bubbles"><circle cx="418" cy="712" r="3"/><circle cx="436" cy="722" r="2"/><circle cx="428" cy="700" r="2.5"/></g>
  <rect class="brass" x="424" y="470" width="12" height="186" fill="#2a1a0c"/>
  <ellipse class="brass" cx="430" cy="530" rx="36" ry="6" fill="#1c120b"/>
  <ellipse class="brass" cx="430" cy="610" rx="18" ry="5" fill="#1c120b"/>
  <path class="brass" d="M410,470 L450,470 L444,448 L416,448 Z" fill="#592815"/>
  <g class="coals"><rect x="418" y="440" width="7" height="6"/><rect x="427" y="438" width="7" height="8"/><rect x="436" y="440" width="7" height="6"/></g>
  <g class="wisps"><path d="M430,432 c-12,-20 10,-34 -2,-58 c-8,-16 12,-28 2,-50"/><path d="M438,434 c10,-18 -8,-30 6,-50"/></g>
  <path class="hose" d="M440,590 C510,560 470,450 336,474 C382,420 384,320 322,286"/>
  <ellipse cx="334" cy="474" rx="13" ry="10" fill="#e8dcc6" class="paw"/>
  <ellipse cx="106" cy="530" rx="13" ry="10" fill="#e8dcc6" class="paw"/>
  <!-- связка мундштуков -->
  <path class="string" d="M148,258 Q210,326 272,258"/>
  {''.join(beads)}
  <!-- зеркало на груди -->
  <circle class="mirror" cx="210" cy="470" r="66"/>
  <circle class="mirror mirror-in" cx="210" cy="470" r="56"/>
  <!-- голова по мотивам лого -->
  <g class="head" transform="translate(60 0) scale(1.5)">
      {head}
  </g>
  <g class="wisps mouth"><path d="M330,262 c10,-16 -6,-28 8,-46 c8,-12 -4,-22 6,-36"/><path d="M340,268 c14,-14 0,-30 16,-44"/></g>
</svg>"""


# выноски у лиса: (id, x, y, точка на лисе в координатах сцены 1100×820)
CALLOUTS = {
    "days1": (90, 96, (470, 122)),
    "days2": (90, 318, (470, 352)),
    "tavern": (120, 540, (392, 486)),
    "channel": (790, 92, (628, 116)),
    "search": (806, 250, (665, 312)),
    "friends": (826, 430, (744, 480)),
}


def build_hall(site):
    scene = pixel_scene_html(site)
    rooms = {r["id"]: r for r in site.rooms}

    def room_link(rid):
        r = rooms[rid]
        n = len(site.room_posts[rid])
        k = site.keeper_of(rid)
        day = f'<i>{esc(r["day"])}</i>' if r.get("day") else "<i>✦</i>"
        return (f'<a class="ilink" href="{r["page"]}" style="--rc:{ROOM_COLOR.get(rid, "#e6ff3a")}">'
                f'<img src="assets/heroes/{k["id"]}.png" alt="" width="16" height="16">{day}'
                f'<span>{esc(r["name"])}</span><b>{n}</b></a>')

    ids = [r["id"] for r in site.rooms]
    week = [i for i in ids if rooms[i].get("day") in ("Пн", "Вт", "Ср", "Чт")]
    rest = [i for i in ids if i not in week]

    def callout(cid, title, inner, side="left", cls=""):
        x, y, _ = CALLOUTS[cid]
        return (f'<div class="callout {side} {cls}" id="co-{cid}" style="left:{x}px;top:{y}px">'
                f'<p class="ctitle">{title}</p>{inner}</div>')

    wires = ""
    for cid, (x, y, (ex, ey)) in CALLOUTS.items():
        sx = x + (230 if cid in ("days1", "days2", "tavern") else 0)
        sy = y + 18
        wires += (f'<g class="wire w-{cid}"><line x1="{sx}" y1="{sy}" x2="{ex}" y2="{ey}"/>'
                  f'<circle cx="{ex}" cy="{ey}" r="9"/></g>')

    neighbors = "".join(f'<a class="ilink" href="{esc(n["url"])}"><i>↗</i><span>{esc(n["title"])}</span></a>'
                        for n in site.s.get("neighbors", []))
    rules = site.hero_data.get("rules", [])
    latest = site.posts[:8]
    news = "".join(f'<li><time datetime="{esc(p["date"])}">{esc(p["date"][:10].replace("-", "."))}</time>'
                   f'<a href="scroll/{p["id"]}.html">{esc(p["title"])}</a></li>' for p in latest)

    threshold = f"""<section class="threshold" aria-labelledby="hall-title">
  <div class="moss moss-l" aria-hidden="true"><div class="moss-glow"></div></div>
  <div class="moss moss-r" aria-hidden="true"><div class="moss-glow"></div></div>
  <div class="stage">
    <div class="logo-big tl" aria-hidden="true"><span class="glitch" data-text="Лисья таверна">Лисья таверна</span><small>з а &nbsp;з е р к а л о м</small></div>
    <div class="logo-big br" aria-hidden="true"><span class="glitch" data-text="Лисья таверна">Лисья таверна</span><small>з а &nbsp;з е р к а л о м</small></div>
    <h1 class="visually-hidden" id="hall-title">{esc(site.s['title'])} — архив канала {esc(site.s['channel_title'])}</h1>
    <svg class="wires" viewBox="0 0 1100 820" aria-hidden="true">{wires}</svg>
    <div class="figure">
      <div class="fox-glow" aria-hidden="true"></div>
      {fox_figure_svg()}
      <a class="enter" href="#orbit"><small>восьмое</small><b>ВОЙТИ</b><small>зеркало</small></a>
    </div>
    {callout("days1", "пн — чт", "".join(room_link(i) for i in week))}
    {callout("days2", "пт — вс · у огня", "".join(room_link(i) for i in rest))}
    {callout("tavern", "таверна", '<a class="ilink" href="guests.html"><img src="assets/heroes/lisivy.png" alt="" width="16" height="16"><i>♣</i><span>Кто в таверне</span></a><a class="ilink" href="#hall-window"><img src="assets/heroes/tomik.png" alt="" width="16" height="16"><i>▣</i><span>Окно в зал</span></a>')}
    <a class="bubble" id="co-channel" style="left:{CALLOUTS['channel'][0]}px;top:{CALLOUTS['channel'][1]}px" href="{esc(site.s['channel_url'])}" rel="noopener"><span class="bubble-ico" aria-hidden="true">✉</span><span>{esc(site.s['channel_url'].replace('https://', ''))}</span><small>канал «{esc(site.s['channel_title'])}»</small></a>
    {callout("search", "картотека осевого", f'<form class="iform" action="search.html" method="get" role="search"><label class="visually-hidden" for="hall-q">Найти свиток</label><input id="hall-q" name="q" type="search" placeholder="что ищешь?"><button type="submit">→</button></form><a class="ilink" href="search.html" style="--rc:{ROOM_COLOR["search"]}"><img src="assets/heroes/osevoy.png" alt="" width="16" height="16"><i>#</i><span>Все {len(site.posts)} свитков</span></a>', "right")}
    {callout("friends", "соседи", neighbors, "right")}
    <div class="warn" id="co-warn">
      <p class="warn-ico" aria-hidden="true">⚠</p>
      <p><b>Доска у входа.</b> {' '.join(esc(x) for x in rules[:3])}<span class="long"> {' '.join(esc(x) for x in rules[6:9])}</span></p>
      <a href="guests.html#rules">читать всю доску →</a>
    </div>
    <div class="newsbox" id="co-news">
      <p class="newsbox-title">вести с тракта</p>
      <ol class="newsbox-list">{news}</ol>
    </div>
  </div>
</section>"""

    # орбита комнат: зеркала, размер — по числу свитков
    orbit_pos = {"hookah": (41, 16), "games": (69, 18), "minis": (88, 45), "ai": (73, 75),
                 "search": (92, 86), "thoughts": (26, 80), "anime": (12, 60), "garden": (26, 36), "shelf": (9, 22)}
    planets = []
    for key, (px_, py_) in orbit_pos.items():
        if key == "search":
            href, name, n, day = "search.html", "Картотека", len(site.posts), "поиск"
        elif key in rooms:
            r = rooms[key]
            href, name, n, day = r["page"], r["sign"], len(site.room_posts[key]), r.get("day") or "✦"
        else:
            continue
        d = 9 + min(n, 200) ** .5 * 1.05 if key != "search" else 13
        k = site.keeper_of(key)
        planets.append(
            f'<a class="planet" href="{href}" style="left:{px_}%;top:{py_}%;--d:{d:.2f}%;--rc:{ROOM_COLOR.get(key, "#e6ff3a")}">'
            f'<span class="p-body"><img class="p-orb" src="assets/heroes/orb-{key}.png" alt="">'
            f'<img class="p-keeper" src="assets/heroes/{k["id"]}.png" alt=""></span>'
            f'<span class="p-label">{esc(name)} <small>{esc(day)} · {n}</small></span></a>')
    orbit = f"""<section class="orbit-wrap" id="orbit" aria-labelledby="orbit-title">
  <h2 class="visually-hidden" id="orbit-title">Комнаты таверны</h2>
  <div class="orbit">
    <svg class="orbit-rings" viewBox="0 0 1100 720" preserveAspectRatio="none" aria-hidden="true">
      <ellipse cx="550" cy="370" rx="520" ry="330"/><ellipse cx="550" cy="370" rx="420" ry="260"/>
      <ellipse cx="550" cy="370" rx="310" ry="190"/><ellipse cx="550" cy="370" rx="200" ry="120"/>
      <path d="M550,40 L1070,370 L550,700 L30,370 Z"/><path d="M200,120 L900,120 L900,620 L200,620 Z"/>
    </svg>
    <a class="planet planet-hall" href="#hall-window" style="left:50%;top:56%;--d:24%;--rc:#ff6a1f">
      <span class="p-body"><span class="p-scene"></span></span>
      <span class="p-label">Общий зал <small>окно · live</small></span></a>
    {''.join(planets)}
    <p class="orbit-hint">Каждая комната — зеркало. Чем больше свитков, тем крупнее.</p>
  </div>
</section>"""

    lines = []
    for r in site.rooms:
        n = len(site.room_posts[r["id"]])
        day = f'{r["day"]} — ' if r.get("day") else ""
        lines.append(f'<li style="--rc:{ROOM_COLOR.get(r["id"], "#e6ff3a")}"><a href="{r["page"]}">{esc(r["name"])}</a><span class="dots"></span>'
                     f'<span class="n">{n}</span>'
                     f'<span class="d">{esc(day)}{esc(r["short"])} · #{esc(r["hashtags"][0])}</span></li>')
    lines.append(f'<li><a href="search.html">Картотека Осевого</a><span class="dots"></span>'
                 f'<span class="n">{len(site.posts)}</span><span class="d">поиск по всему каналу</span></li>')
    p0 = site.posts[0] if site.posts else None
    fresh = ""
    if p0:
        tags = "".join(f'<a class="chip chip-sm" href="search.html?tag={esc(t)}">#{esc(t)}</a>' for t in p0["hashtags"][:5])
        fresh = (f'<p class="meta"><time datetime="{esc(p0["date"])}">{ru_date(p0["date"])}</time></p>'
                 f'<h3><a href="scroll/{p0["id"]}.html">{esc(p0["title"])}</a></h3>'
                 f'<p class="excerpt">{esc(p0["excerpt"])}</p><p class="tags">{tags}</p>')
    log = "".join(f'<li><time datetime="{esc(p["date"])}">{esc(p["date"][:10].replace("-", "."))}</time> '
                  f'<a href="scroll/{p["id"]}.html">{esc(p["title"])}</a></li>' for p in site.posts[1:13])
    host = site.keeper_of("hookah")
    status = [("чаша", "дымит", "on"), ("хвост", "тлеет", "on"), ("Уголёк", "раскалён, молчит", "on"),
              ("Фомичей", "11 · полив не решён", "warn"), ("Гаврилыч", "уверен", "warn"), ("осы", "не слышно", "off")]
    status_html = "".join(f'<li class="st-{c}"><span>{esc(a)}</span><b>{esc(b)}</b></li>' for a, b, c in status)
    ticker = " ✦ ".join(esc(p["title"]) for p in site.posts[:8])

    dash = f"""<section class="panel window" id="hall-window">
  <h2 class="bar">Окно в общий зал <small>наведи на предмет — и войди</small></h2>
  <div class="scene-frame">
    {scene}
  </div>
  <div class="ticker" aria-label="Свежие свитки"><div class="ticker-track"><span>вести с тракта ✦ {ticker} ✦ </span><span aria-hidden="true">вести с тракта ✦ {ticker} ✦ </span></div></div>
</section>
<div class="dash">
  <div class="dash-col">
    <section class="panel">
      <h2 class="bar">Свежий свиток <span class="bar-ico" aria-hidden="true">≋</span></h2>
      <div class="panel-in fresh">{fresh}</div>
      <a class="panel-foot" href="search.html">все свитки</a>
    </section>
    <section class="panel">
      <h2 class="bar">Летопись <span class="bar-ico" aria-hidden="true">☰</span></h2>
      <ol class="panel-in log">{log}</ol>
      <a class="panel-foot" href="search.html">вся картотека</a>
    </section>
  </div>
  <div class="dash-col">
    <section class="panel">
      <h2 class="bar">Статус <span class="bar-ico" aria-hidden="true">∿</span></h2>
      <ul class="panel-in status-list">{status_html}</ul>
    </section>
    <section class="panel">
      <h2 class="bar">Передача <span class="bar-ico" aria-hidden="true">⌁</span></h2>
      <div class="panel-in transmission"><p class="quote" data-quotes='{esc(json.dumps(site.quotes, ensure_ascii=False))}'>{esc(site.quotes[0])}</p></div>
    </section>
    <section class="panel">
      <h2 class="bar">Хозяин <span class="bar-ico" aria-hidden="true">✦</span></h2>
      <div class="panel-in host">
        <img class="host-pic" src="assets/heroes/{esc(host['id'])}.png" alt="{esc(host['name'])}" width="96" height="96">
        <div><h3>{esc(host['name'])}</h3><p class="says">«{esc(host.get('quote', ''))}»</p>
        <p>{esc(host['blocks'][0][1] if host.get('blocks') else '')}</p></div>
      </div>
      <a class="panel-foot" href="guests.html">кто ещё в таверне</a>
    </section>
    <section class="panel">
      <h2 class="bar">Указатель <span class="bar-ico" aria-hidden="true">⌖</span></h2>
      <ul class="panel-in dir">{''.join(lines)}</ul>
    </section>
  </div>
</div>"""
    site.page("index.html", site.s["title"], threshold + orbit + dash, root="", desc=site.s["tagline"], scene=True)


VERDICTS = {"любимое": (5, "❤"), "советую": (4, "✦"), "приятно": (3, "☙"), "спорно": (2, "⚖"),
            "мимо": (1, "✗"), "без вердикта": (0, "…")}
STATUS_CLASS = {"растёт": "ok", "цветёт": "bloom", "плодоносит": "fruit", "урожай собран": "fruit", "спит": "sleep",
                "почило": "dead", "покрашено": "ok", "в процессе": "wip", "собрано": "bloom", "грунт": "sleep",
                "куча позора": "dead", "прочитано": "ok", "просмотрено": "ok", "смотрю": "wip", "брошено": "dead",
                "в планах": "sleep"}


def verdict_badge(v):
    rank, icon = VERDICTS.get(v, (0, "…"))
    return f'<span class="verdict v{rank}" title="Вердикт хозяина">{icon} {esc(v)}</span>'


def post_more(site, pid, label="читать свиток →"):
    link = site.post_link(pid)
    return f' <a href="{esc(link)}">{label}</a>' if link else ""


def quick_tags(posts, limit=16):
    counts = {}
    for p in posts:
        for t in p["hashtags"]:
            counts[t] = counts.get(t, 0) + 1
    return "".join(f'<a class="chip" href="#feed" data-quicktag="{esc(t)}">#{esc(t)} <sup>{n}</sup></a>'
                   for t, n in sorted(counts.items(), key=lambda kv: -kv[1])[:limit])


def build_ai(site, r):
    posts = site.room_posts[r["id"]]
    pins = ""
    for it in site.cat.get("ai", {}).get("pinned", []):
        url = it.get("url") or "#feed"
        ext = url.startswith("http")
        pins += (f'<li class="pin">{stamp(it)}<a href="{esc(url)}"{" rel=noopener target=_blank" if ext else ""}>'
                 f'{esc(it["title"])}{" ↗" if ext else ""}</a><span>{esc(it.get("note", ""))}</span></li>')
    body = site.room_head(r) + f"""
<section class="parchment quick">
  <h2>Быстрые ярлыки</h2>
  <div class="quick-grid">
    <div><h3>Закреплённые свитки</h3><ul class="pins">{pins or '<li class="empty">Пока ничего не закреплено.</li>'}</ul></div>
    <div><h3>Темы</h3><p class="chips">{quick_tags(posts) or '<span class="empty">Тем пока нет.</span>'}</p>
    <p class="tiny">Жми на тему — ниже останутся только нужные свитки.</p></div>
  </div>
</section>
""" + site.feed(posts, "", "Свитки из архивов", big=True)
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def build_feed_room(site, r):
    posts = site.room_posts[r["id"]]
    body = site.room_head(r) + site.feed(posts, "", f"Свитки: {r['name'].lower()}", big=True)
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def build_hookah(site, r):
    items = site.cat.get("hookah", {}).get("items", [])
    cards = []
    for it in items:
        mix = "".join(f"<li>{esc(m)}</li>" for m in it.get("mix", []))
        rank = VERDICTS.get(it.get("verdict", ""), (0,))[0]
        notes = it.get("notes", [])
        extra = [it["strength"]] if it.get("strength") else []
        search = " ".join([it["name"], it.get("kind", ""), " ".join(it.get("flavors", [])), " ".join(it.get("mix", [])),
                           " ".join(notes), it.get("note", ""), it.get("verdict", "")]).lower()
        cards.append(f"""<article class="card recipe entry" data-search="{esc(search)}" data-flavors="{esc('|'.join(it.get('flavors', [])))}" data-notes="{esc('|'.join(notes))}" data-verdict="{esc(it.get('verdict', ''))}" data-kind="{esc(it.get('kind', ''))}" data-rank="{rank}" data-date="{esc(it.get('date', ''))}" data-name="{esc(it['name'].lower())}">
  {stamp(it)}
  <p class="type">{esc(it.get('kind', ''))}{' · ' + esc(it['strength']) if it.get('strength') else ''}</p>
  <h3>{esc(it['name'])}</h3>
  <p>{verdict_badge(it.get('verdict', 'без вердикта'))}</p>
  {f'<ul class="mix">{mix}</ul>' if mix else ''}
  <p class="note">{esc(it.get('note', ''))}</p>
  <p class="tags">{''.join(f'<span class="chip chip-sm">{esc(f)}</span>' for f in it.get('flavors', []) + notes)}</p>
  <p class="meta">{ru_date(it.get('date', ''))}{post_more(site, it.get('post'))}</p>
</article>""")
    flavors = [f for it in items for f in it.get("flavors", [])]
    notes = [n for it in items for n in it.get("notes", [])]
    body = site.room_head(r) + f"""
<section class="parchment catalog">
  <h2>Книга забивок <small class="count" data-count-for="hookah-list">{len(items)}</small></h2>
  <p class="lead-in">Всё, что Кальяныч забивал и о чём писал в канале. Вердикты — его словами, у каждой записи ссылка на свиток.</p>
  <div class="filterbox" data-target="#hookah-list">
    <label class="search-field"><span>Вкус, бренд, слово</span><input type="search" data-search placeholder="вишня, Trofimoff, кола…"></label>
    {facet_chips(flavors, 'flavors', 'all', 'Вкус:')}
    {facet_chips(notes, 'notes', 'all', 'Особое:')}
    {facet_chips([it.get('verdict', '') for it in items], 'verdict', 'any', 'Вердикт:')}
    <div class="row-controls">
      <label>Что <select data-eq="kind"><option value="">всё</option><option value="табак">табаки</option><option value="микс">миксы</option></select></label>
      <label>Порядок <select data-sort><option value="rank-desc">лучшие</option><option value="date-desc">новые</option><option value="name-asc">по имени</option></select></label>
      <button type="button" class="btn-link" data-reset>сбросить</button>
    </div>
  </div>
  <div class="cards cards-3" id="hookah-list">{''.join(cards)}</div>
  <p class="nothing" hidden>Такой забивки в книге нет. Может, изобретёшь?</p>
</section>
""" + site.feed(site.room_posts[r["id"]], "", "Свитки из горницы")
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def diary_entry(site, d):
    pic = f'<img src="{esc(d["photo"])}" alt="" loading="lazy">' if d.get("photo") else ""
    return (f'<li><time datetime="{esc(d["date"])}">{ru_date(d["date"])}</time>{pic}'
            f'<p>{esc(d["text"])}{post_more(site, d.get("post"), "свиток →")}</p></li>')


def build_garden(site, r):
    items = site.cat.get("garden", {}).get("items", [])
    cards = []
    for it in items:
        days = (site.today - dt.date.fromisoformat(it["since"])).days if it.get("since") else None
        since = ("в таверне с " + ru_date(it["since"])) if it.get("since") else esc(it.get("since_text", ""))
        age = f' · {days} {plural(days, "день", "дня", "дней")}' if days is not None else ""
        diary = "".join(diary_entry(site, d) for d in it.get("diary", []))
        care = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in it.get("care", {}).items())
        pic = (f'<img src="{esc(it["photo"])}" alt="{esc(it["name"])}" loading="lazy">' if it.get("photo")
               else '<img class="pix" src="assets/scene/icon-garden.png" alt="">')
        st = it.get("status", "")
        last = max((d["date"] for d in it.get("diary", [])), default=it.get("since", ""))
        search = " ".join([it["name"], it.get("latin", ""), st, it.get("place", "")] + [d["text"] for d in it.get("diary", [])]).lower()
        cards.append(f"""<article class="card plant entry" data-search="{esc(search)}" data-status="{esc(st)}" data-date="{esc(last)}" data-name="{esc(it['name'].lower())}">
  {stamp(it)}
  <div class="plant-top">
    <div class="plant-pic">{pic}</div>
    <div>
      <h3>{esc(it['name'])}</h3>
      <p class="latin">{esc(it.get('latin', ''))}</p>
      <p><span class="status s-{STATUS_CLASS.get(st, 'ok')}">{esc(st)}</span></p>
      <p class="meta">{since}{age}{' · ' + esc(it['place']) if it.get('place') else ''}</p>
    </div>
  </div>
  <dl class="care">{care}</dl>
  <details class="diary"><summary>Дневник роста ({len(it.get('diary', []))})</summary><ol class="timeline">{diary}</ol></details>
</article>""")
    alive = sum(1 for it in items if it.get("status") != "почило")
    body = site.room_head(r) + f"""
<section class="parchment catalog">
  <h2>Зелёные подопытные <small class="count" data-count-for="garden-list">{len(items)}</small></h2>
  <p class="lead-in">Живы {alive} из {len(items)}. Остальные — в кладбищенской книге: кто сдох, тот лох.</p>
  <div class="filterbox" data-target="#garden-list">
    <label class="search-field"><span>Растение или запись дневника</span><input type="search" data-search placeholder="лимон, клещ, стратификация…"></label>
    {facet_chips([it.get('status', '') for it in items], 'status', 'any', 'Состояние:')}
    <div class="row-controls"><label>Порядок <select data-sort><option value="date-desc">свежие записи</option><option value="name-asc">по имени</option></select></label><button type="button" class="btn-link" data-reset>сбросить</button></div>
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
        st = it.get("status", "")
        search = " ".join([it["name"], f["name"], st, it.get("note", "")]).lower()
        cards.append(f"""<figure class="card mini entry" style="--fc:{esc(f['color'])}" data-search="{esc(search)}" data-faction="{esc(f['name'])}" data-status="{esc(st)}" data-date="{esc(it.get('date', ''))}" data-name="{esc(it['name'].lower())}">
  {stamp(it)}
  <div class="mini-pic">{pic}</div>
  <figcaption><b>{esc(it['name'])}</b><span class="banner">{esc(f['name'])}</span>
  <span class="status s-{STATUS_CLASS.get(st, 'ok')}">{esc(st)}</span>
  <small>{esc(it.get('note', ''))}</small>
  <small class="meta">{ru_date(it.get('date', ''))}{post_more(site, it.get('post'), 'свиток →')}</small></figcaption>
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
  <h2>Воинства на полках <small class="count" data-count-for="minis-list">{len(items)}</small></h2>
  <ul class="factions">{legend}</ul>
  <p class="shame">Непокрашенного в куче позора: <b>{shame}</b>. Плюмбий командует ими, хоть и сам наполовину в грунте. Хозяин вставляет магниты.</p>
  <div class="filterbox" data-target="#minis-list">
    {facet_chips([factions.get(it.get('faction'), {}).get('name', it.get('faction', '')) for it in items], 'faction', 'any', 'Фракция:')}
    {facet_chips([it.get('status', '') for it in items], 'status', 'any', 'Готовность:')}
    <div class="row-controls"><label class="search-field inline"><span>Поиск</span><input type="search" data-search placeholder="дредноут, магниты, грунт…"></label><label>Порядок <select data-sort><option value="date-desc">новые</option><option value="date-asc">старые</option><option value="name-asc">по имени</option></select></label><button type="button" class="btn-link" data-reset>сбросить</button></div>
  </div>
  <div class="cards gallery" id="minis-list">{''.join(cards)}</div>
  <p class="nothing" hidden>Таких воинов не нашлось. Может, они ещё в коробке.</p>
</section>
""" + site.feed(site.room_posts[r["id"]], "", "Свитки из мастерской")
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def build_shelf(site, r):
    types = r.get("types")
    items = [it for it in site.cat.get("shelf", {}).get("items", []) if not types or it.get("type") in types]
    cards = []
    for it in items:
        t = it.get("type", "книга")
        hue = sum(map(ord, it["title"])) % 360
        rank = VERDICTS.get(it.get("verdict", ""), (0,))[0]
        search = " ".join([it["title"], it.get("author", ""), t, " ".join(it.get("genres", [])), it.get("note", ""), it.get("verdict", "")]).lower()
        cards.append(f"""<article class="card book entry" style="--h:{hue}" data-search="{esc(search)}" data-type="{esc(t)}" data-status="{esc(it.get('status', ''))}" data-verdict="{esc(it.get('verdict', ''))}" data-rank="{rank}" data-name="{esc(it['title'].lower())}" data-date="{esc(it.get('date', ''))}">
  {stamp(it)}
  <div class="spine" aria-hidden="true"><span>{esc(it['title'])}</span></div>
  <div class="book-body">
    <p class="type">{esc(t)}</p>
    <h3>{esc(it['title'])}</h3>
    {f'<p class="author">{esc(it["author"])}</p>' if it.get('author') else ''}
    <p>{verdict_badge(it.get('verdict', 'без вердикта'))}</p>
    <p class="verdict-text">{esc(it.get('note', ''))}</p>
    <p class="meta"><span class="status s-{STATUS_CLASS.get(it.get('status', ''), 'ok')}">{esc(it.get('status', ''))}</span> {' · '.join(esc(g) for g in it.get('genres', []))}{post_more(site, it.get('post'), 'свиток →')}</p>
  </div>
</article>""")
    title = "На экране" if r["id"] == "anime" else "На полке"
    body = site.room_head(r) + f"""
<section class="parchment catalog">
  <h2>{title} <small class="count" data-count-for="{r['id']}-list">{len(items)}</small></h2>
  <div class="filterbox" data-target="#{r['id']}-list">
    <label class="search-field"><span>Название, автор, слово</span><input type="search" data-search placeholder="Берсерк, MAPPA, Warhammer…"></label>
    {facet_chips([it.get('type', '') for it in items], 'type', 'any', 'Что:') if len(set(it.get('type') for it in items)) > 1 else ''}
    {facet_chips([it.get('verdict', '') for it in items], 'verdict', 'any', 'Вердикт:')}
    {facet_chips([it.get('status', '') for it in items], 'status', 'any', 'Статус:')}
    <div class="row-controls"><label>Порядок <select data-sort><option value="rank-desc">лучшие</option><option value="date-desc">новые</option><option value="name-asc">по имени</option></select></label><button type="button" class="btn-link" data-reset>сбросить</button></div>
  </div>
  <div class="cards cards-2" id="{r['id']}-list">{''.join(cards)}</div>
  <p class="nothing" hidden>Такого здесь нет. Пока.</p>
</section>
""" + site.feed(site.room_posts[r["id"]], "", "Свитки с полки" if r["id"] != "anime" else "Свитки с экрана")
    site.page(r["page"], r["name"], body, room=r["id"], desc=r["about"])


def hero_card(site, h, big=False):
    rooms = {r["id"]: r for r in site.rooms}
    watch = []
    for rid in [h.get("room")] + [x for x in h.get("rooms", []) if x != h.get("room")]:
        if rid in rooms:
            watch.append(f'<a href="{rooms[rid]["page"]}">{esc(rooms[rid]["name"])}</a>')
        elif rid == "search":
            watch.append('<a href="search.html">Картотека</a>')
    blocks = "".join(f'<p>{f"<b>{esc(a)}.</b> " if a else ""}{esc(b)}</p>' for a, b in h.get("blocks", []))
    stats = "".join(f'<div class="irow"><span class="ik">{esc(a)}</span><span class="iv">{esc(b)}</span></div>'
                    for a, b in h.get("stats", []))
    if watch:
        stats += f'<div class="irow irow-watch"><span class="ik">смотрит за</span><span class="iv">{" · ".join(watch)}</span></div>'
    color = ROOM_COLOR.get(h.get("room"), "#e6ff3a")
    return f"""<article class="hero{' hero-big' if big else ''}" id="{esc(h['id'])}" style="--rc:{color}">
  <div class="hero-mirror"><img class="rh-orb" src="assets/heroes/orb-{esc(h.get('room') if h.get('room') in ROOM_COLOR else 'search')}.png" alt=""><img class="hero-pic" src="assets/heroes/{esc(h['id'])}.png" alt="Пиксельный портрет: {esc(h['name'])}"></div>
  <div class="hero-text">
    <p class="hero-tag">{esc(h.get('tag', ''))}</p>
    <h3>{esc(h['name'])}</h3>
    <p class="hero-quote">«{esc(h.get('quote', ''))}»</p>
    <div class="hero-blocks">{blocks}</div>
    <div class="inspect">{stats}</div>
  </div>
</article>"""


def build_guests(site):
    d = site.hero_data
    heroes = d.get("heroes", [])
    host = [h for h in heroes if h.get("group") == "host"]
    fox = [h for h in heroes if h.get("group") == "fox"]
    residents = [h for h in heroes if h.get("group") == "resident"]
    intro = "".join(f"<p>{esc(p)}</p>" for p in d.get("intro", []))
    signs = "".join(f'<span class="sign-tag">{esc(s)}</span>' for s in d.get("signs", []))
    world = "".join(f'<div class="wk"><dt>{esc(a)}</dt><dd>{esc(b)}</dd></div>' for a, b in d.get("world", []))
    rules = "".join(f"<li>{esc(r)}</li>" for r in d.get("rules", []))
    bowls = "".join(f'<li><b>{esc(a)}</b><span>{esc(b)}</span><em>плата: {esc(c)}</em></li>' for a, b, c in d.get("bowls", []))
    roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    jars = "".join(f'<button type="button" class="jar" aria-expanded="false"><span class="jar-lid"></span>'
                   f'<span class="jar-no">банка {roman[i] if i < len(roman) else i + 1}</span>'
                   f'<span class="jar-label">{esc(j)}</span></button>' for i, j in enumerate(d.get("jars", [])))
    book = "".join(f'<li><span>{esc(a)}</span>{f"<small>— {esc(b)}</small>" if b else ""}</li>' for a, b in d.get("guestbook", []))
    keepers = "".join(f'<a class="ilink" href="#{esc(h["id"])}" style="--rc:{ROOM_COLOR.get(h.get("room"), "#e6ff3a")}">'
                      f'<img src="assets/heroes/{esc(h["id"])}.png" alt="" width="16" height="16"><span>{esc(h["name"])}</span></a>'
                      for h in heroes)
    body = f"""<section class="room-head guests-head" style="--rc:#ff6a1f">
  <div class="rh-mirror" aria-hidden="true"><img class="rh-orb" src="assets/heroes/orb-hookah.png" alt=""><img class="rh-keeper" src="assets/heroes/kalyanych.png" alt=""></div>
  <div class="rh-text">
    <p class="crumbs"><a href="index.html">общий зал</a> <span>›</span> кто в таверне</p>
    <p class="kicker">{esc(d.get('place', ''))}</p>
    <h1>Кто в таверне</h1>
    <div class="intro">{intro}</div>
    <p class="signs">{signs}</p>
  </div>
</section>
<nav class="panel who-nav" aria-label="Герои">
  <h2 class="bar">Постояльцы и хозяева</h2>
  <div class="panel-in who-links">{keepers}<a class="ilink" href="#rules"><i>⚠</i><span>Доска у входа</span></a><a class="ilink" href="#bowls"><i>♨</i><span>Что в чаше</span></a><a class="ilink" href="#jars"><i>▥</i><span>Полка банок</span></a><a class="ilink" href="#book"><i>✎</i><span>Гостевая</span></a><a class="ilink" href="#world"><i>⌖</i><span>Окружающий архив</span></a></div>
</nav>
<section class="panel">
  <h2 class="bar">Хозяин <small>держит заведение</small></h2>
  <div class="panel-in">{''.join(hero_card(site, h, True) for h in host)}</div>
</section>
<section class="panel">
  <h2 class="bar">Второй лис</h2>
  <div class="panel-in">{''.join(f'<p class="lead-in">{esc(h.get("lead", ""))}</p>' + hero_card(site, h, True) for h in fox)}</div>
</section>
<section class="panel">
  <h2 class="bar">Постояльцы <small>каждый присматривает за своей комнатой</small></h2>
  <div class="panel-in">
    <p class="lead-in">Шестеро, которые были здесь ещё до того, как Лис принял заведение. Ни один не платит, ни один не уходит. Без них таверна не то чтобы опустеет — она перестанет держаться.</p>
    <div class="heroes-grid">{''.join(hero_card(site, h) for h in residents)}</div>
  </div>
</section>
<div class="dash">
  <div class="dash-col">
    <section class="panel warn-panel" id="rules">
      <h2 class="bar">Доска у входа <small>читать до того, как сесть</small></h2>
      <ol class="panel-in rules">{rules}</ol>
    </section>
    <section class="panel" id="jars">
      <h2 class="bar">Полка над лестницей</h2>
      <div class="panel-in">
        <p class="lead-in">{esc(d.get('jars_note', ''))}</p>
        <div class="jars">{jars}</div>
        <p class="jar-hint" aria-live="polite">Возьмите банку с полки.</p>
      </div>
    </section>
  </div>
  <div class="dash-col">
    <section class="panel" id="bowls">
      <h2 class="bar">Что в чаше</h2>
      <div class="panel-in"><p class="lead-in">{esc(d.get('bowls_note', ''))}</p><ul class="bowls">{bowls}</ul>
      <p class="tiny">Настоящие забивки хозяина — в горнице: <a href="hookah.html">Дым и покой →</a></p></div>
    </section>
    <section class="panel" id="book">
      <h2 class="bar">Гостевая <small>лежит у двери на цепочке</small></h2>
      <ol class="panel-in guestbook">{book}</ol>
    </section>
  </div>
</div>
<section class="panel" id="world">
  <h2 class="bar">Окружающий архив <small>что здесь считается общеизвестным</small></h2>
  <dl class="panel-in world">{world}</dl>
  <p class="panel-in how"><b>Как найти.</b> {esc(d.get('how_to_find', ''))}</p>
</section>"""
    site.page("guests.html", "Кто в таверне", body, room="guests",
              desc="Лис Кальяныч, Герой Шутливый Лисивый и постояльцы Лисьей таверны за зеркалом")


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
    pseudo = {"id": "search", "name": "Картотека Деда Осевого",
              "epigraph": "Не привязано к сетке — значит, не существует.",
              "about": f"Дед Осевой подписал все {len(site.posts)} свитков канала: ищи по словам, хэштегам и комнатам."}
    body = site.room_head(pseudo, count=len(site.posts)) + f"""
<section class="parchment" id="search-app">
  <form class="ask" role="search" onsubmit="return false">
    <div class="ask-row"><input id="q" type="search" placeholder="слово, имя, вкус…" autocomplete="off" aria-label="Что искать"><select id="room" aria-label="Комната"><option value="">все комнаты</option>{opts}</select></div>
  </form>
  <div class="chips" id="tagchips">{chips}</div>
  <p class="result-count" id="rc" aria-live="polite"></p>
  <ol class="results" id="results"></ol>
  <noscript><p>Без JavaScript Осевой не ищет, но все свитки есть в комнатах таверны.</p></noscript>
</section>
<script src="assets/search-index.js"></script>"""
    site.page("search.html", "Картотека Деда Осевого", body, room="search", desc="Поиск по всем постам канала")


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
    urls = [base] + [base + r["page"] for r in site.rooms] + [base + "search.html", base + "guests.html"]
    urls += [f"{base}scroll/{p['id']}.html" for p in site.posts]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n"
    (SITE / "sitemap.xml").write_text(xml, encoding="utf-8")


BUILDERS = {"ai": build_ai, "hookah": build_hookah, "garden": build_garden, "minis": build_minis,
            "shelf": build_shelf, "feed": build_feed_room}


def main():
    ap = argparse.ArgumentParser(description="Собрать Трактирную книгу")
    ap.add_argument("--export", help="папка экспорта Telegram (ChatExport_…)")
    ap.add_argument("--no-media", action="store_true", help="не копировать картинки из экспорта")
    args = ap.parse_args()

    if args.export:
        run_import(args.export, args.no_media)

    cfg = load_json(SRC / "config.json")
    catalogs = {p.stem: load_json(p) for p in (SRC / "catalog").glob("*.json")}
    posts = [p for p in enrich(load_posts(), cfg["rooms"]) if p["title"] != "Пустой свиток"]
    site = Site(cfg, posts, catalogs)

    build_hall(site)
    for r in site.rooms:
        BUILDERS.get(r.get("kind", "feed"), build_feed_room)(site, r)
    build_guests(site)
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
