#!/usr/bin/env python3
"""Пиксельный общий зал Лисьей таверны.

Рисует сцену 480×280 с освещением (очаг, свечи, магический шар), дизерингом и обводками,
в 4 кадрах анимации (огонь, дым, шестерни, глаз в шаре, бобыль). Результат:

  assets/scene/frames.png      — 4 кадра в ряд (CSS листает их)
  assets/scene/hl-<id>.png     — подсветка предмета при наведении
  assets/scene/icon-<id>.png   — иконки комнат (вырезки из сцены)
  _src/hotspots.json           — где лежат предметы (для build.py)

Нужны Pillow и numpy (pip install pillow numpy). Запускать только если хочется перерисовать зал.
"""
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

W, H = 480, 280
SRC = Path(__file__).resolve().parent
OUT = SRC.parent / "assets" / "scene"

RAMPS = {
    "stone": ["#0f0b12", "#1b141c", "#281d25", "#36252c", "#463033", "#583c3b", "#6e4c45", "#885f51"],
    "grey": ["#121016", "#211e26", "#312d35", "#433e45", "#575057", "#6d6468", "#877c7d", "#a39794"],
    "wood": ["#120c0b", "#21150f", "#321d13", "#452717", "#5a321b", "#724021", "#8c5129", "#a86535", "#c67f47"],
    "metal": ["#101016", "#1f2029", "#323441", "#4a4e60", "#686f84", "#8d97aa", "#b8c0ce", "#e8edf5"],
    "brass": ["#1c120b", "#392311", "#5e3814", "#86561b", "#ae7824", "#d49f3e", "#eec766", "#fff0a8"],
    "glass": ["#0a1322", "#112646", "#143d75", "#1b5ea3", "#2c86cc", "#56aee6", "#96d4f8", "#e0f5ff"],
    "plant": ["#0a130e", "#112418", "#193720", "#234e25", "#31662a", "#488431", "#69a33c", "#96c858"],
    "red": ["#180a0d", "#320e15", "#53131b", "#781a21", "#9e2528", "#c33c33", "#dd6048", "#f28d66"],
    "blue": ["#0b0e1c", "#141b37", "#1d2a54", "#293e74", "#395692", "#5074ae", "#7496c8"],
    "green": ["#0a140e", "#122818", "#1b3c22", "#27532a", "#376b33", "#4f8740"],
    "purple": ["#130b19", "#251536", "#3a1f50", "#522c69", "#6c3d82", "#89539b"],
    "parch": ["#281a13", "#463121", "#6a4e33", "#8f704c", "#b39267", "#d1b487", "#e9d3a7", "#faefcf"],
    "terra": ["#1a0d09", "#37180f", "#592815", "#7d371b", "#a24a22", "#c46431", "#dd874b"],
    "skin": ["#281512", "#4c281e", "#774030", "#a56347", "#cc8f6d", "#eabd97"],
    "fur": ["#1b0c08", "#3a150b", "#66220f", "#963511", "#c65216", "#e67624", "#f69c42", "#ffc574"],
    "cream": ["#29211e", "#574740", "#8b776a", "#bdab99", "#e1d4c2", "#faf3e6"],
    "bone": ["#221c18", "#473d35", "#766a5b", "#a79a84", "#d4c9b2", "#f3ebd6"],
    "ink": ["#0b080b", "#161119", "#211a24"],
    "fire": ["#561407", "#95280b", "#cf4811", "#ef7819", "#fba52b", "#ffd259", "#fff09a", "#fffbe6"],
    "sky": ["#04050d", "#090d1f", "#0f1634", "#17214b", "#202d62"],
    "star": ["#6c7298", "#c6cbef", "#fffbe0"],
    "screen": ["#030d08", "#071c11", "#0c301d", "#134b2b", "#20733c", "#36a256", "#6ade86", "#b4ffc6"],
    "orb": ["#092030", "#0e384c", "#15566d", "#1e7a90", "#33a2b2", "#61c8d0", "#a2eaea", "#e6ffff"],
    "brew": ["#0e220f", "#1b4719", "#2c7022", "#479c30", "#73c548", "#aee976"],
    "smoke": ["#595560", "#827c84", "#aca5aa", "#d2cbcb", "#efe9e4"],
    "cork": ["#281910", "#4b301e", "#704d2d", "#966c40", "#b48955", "#cfa66d"],
    "hl": ["#fee761"],
    "kok": ["#141a18", "#232d2a", "#34413d", "#4a5a55", "#62756f", "#7f928b", "#a3b3ad"],
    "eye": ["#e6ff3a"],
    "tin": ["#16181f", "#2a2e3a", "#434857", "#5f6578", "#7e8598", "#a0a8ba", "#c6ccda"],
    "tvfur": ["#1b0c08", "#3a150b", "#66220f", "#963511", "#c65216", "#e67624", "#f69c42", "#ffc574"],
    "tvcream": ["#29211e", "#574740", "#8b776a", "#bdab99", "#e1d4c2", "#faf3e6"],
}
MATS = list(RAMPS)
MID = {m: i for i, m in enumerate(MATS)}
EMISSIVE = {"fire", "sky", "star", "screen", "brew", "orb", "hl", "tvfur", "tvcream", "eye"}
RGB = [np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in RAMPS[m]], np.uint8) for m in MATS]
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16
BAYER = np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W]

OBJ = {"garden": 1, "shelf": 2, "hearth": 3, "board": 4, "ai": 5, "minis": 6, "hookah": 7,
       "fox": 8, "cat": 9, "snail": 10, "knight": 11, "barrel": 12, "chandelier": 13, "table": 14, "screen": 15,
       "plumbiy": 16}
HOT = {  # ключ — id комнаты из config.json (search — поиск), значение — предметы сцены
    "garden": ["garden"], "shelf": ["shelf"], "thoughts": ["hearth"], "search": ["board"],
    "ai": ["ai"], "anime": ["screen"], "minis": ["minis"], "games": ["barrel"], "hookah": ["hookah", "table", "fox"],
}


class Canvas:
    def __init__(self):
        self.mat = np.zeros((H, W), np.int16)
        self.lvl = np.zeros((H, W), np.float32)
        self.obj = np.zeros((H, W), np.int16)
        self.lights = []
        yy, xx = np.mgrid[0:H, 0:W]
        self.xx, self.yy = xx, yy
        self.rng = np.random.default_rng(3)
        self.noise = self.rng.uniform(-.5, .5, (H, W)).astype(np.float32)

    # маски
    def _m(self, fn):
        im = Image.new("1", (W, H))
        fn(ImageDraw.Draw(im))
        return np.array(im, bool)

    def rect(self, x0, y0, x1, y1):
        return self._m(lambda d: d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=1))

    def poly(self, pts):
        return self._m(lambda d: d.polygon(pts, fill=1))

    def ell(self, x0, y0, x1, y1):
        return self._m(lambda d: d.ellipse([x0, y0, x1 - 1, y1 - 1], fill=1))

    def line(self, pts, w=1):
        return self._m(lambda d: d.line(pts, fill=1, width=w))

    def paint(self, mask, mat, lvl, obj=None, tex=0.0):
        lv = lvl if np.isscalar(lvl) else lvl[mask]
        self.mat[mask] = MID[mat]
        self.lvl[mask] = (lv + self.noise[mask] * tex) if tex else lv
        if obj is not None:
            self.obj[mask] = OBJ[obj] if isinstance(obj, str) else obj

    def px(self, x, y, mat, lvl, obj=None):
        if 0 <= x < W and 0 <= y < H:
            self.mat[y, x], self.lvl[y, x] = MID[mat], lvl
            if obj is not None:
                self.obj[y, x] = OBJ[obj]

    def sprite(self, x, y, rows, legend, obj=None, flip=False):
        for j, row in enumerate(rows):
            if flip:
                row = row[::-1]
            for i, ch in enumerate(row):
                if ch in legend:
                    m, l = legend[ch]
                    self.px(x + i, y + j, m, l, obj)

    def light(self, x, y, r, i):
        self.lights.append((x, y, r, i))

    def render(self, ambient=0.16, gain=3.6):
        L = np.full((H, W), ambient, np.float32)
        for x, y, r, i in self.lights:
            d = np.sqrt((self.xx - x) ** 2 + ((self.yy - y) * 1.1) ** 2) / r
            L += i * np.clip(1 - d, 0, 1) ** 1.7
        shade = self.lvl + (L - 0.5) * gain
        emis = np.isin(self.mat, [MID[m] for m in EMISSIVE])
        shade = np.where(emis, self.lvl, shade)
        # обводка по краям предметов
        o = self.obj
        edge = np.zeros_like(o, bool)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(np.roll(o, dy, 0), dx, 1)
            edge |= (o > 0) & (sh != o) & ~((sh > 0) & (sh < o) & False)
        shade = np.where(edge & ~emis, np.minimum(shade, 0.4), shade)
        out = np.zeros((H, W, 3), np.uint8)
        for mi, ramp in enumerate(RGB):
            sel = self.mat == mi
            if not sel.any():
                continue
            q = np.floor(shade[sel] + BAYER[sel]).astype(int)
            out[sel] = ramp[np.clip(q, 0, len(ramp) - 1)]
        return out


# ─────────────────────────── спрайты ───────────────────────────

FOX = """
......kk.......kk..........
.....kOOk.....kOOk.........
.....kOwOk...kOwOk.........
.....kOwwOkkkOwwOk.........
....kOOOOOOOOOOOOOk........
....kOOOOOOOOOOOOOOk.......
...kOOOOOOOOkeOOOOOOk......
...kOOOOOOOOkeOOOOOOOkk....
...kOOOOOOOOOOOOOOWWWWWkk..
...koOOOOOOOOOOOWWWWWWWWWk.
....koOOOOOOOOWWWWWWWWWkkk.
.....kooOOOOOWWWWWWkkkk....
......kkoooWWWWWWkk........
........kkGGGGGkk..........
.......kGGGGGGGGGk.........
......kGGGGGGGGGGGk........
.....kGGGGGGdGGGGGGk.......
.....kGGGGGGdGGGGGGGkk.....
.....kGGGGGGdGGGGGkOOOOk...
.....kGGGGGGdGGGGkOOOOOOk..
.....kdGGGGGdGGGGGkkkkkk...
.....kdGGGGGdGGGGGGk.......
..kkkkdGGGGGdGGGGGGk.......
.kOOOkdyyyyyyyyyyyyk.......
kOOOOkdGGGGGGGGGGGGGk......
kOOOOkkGGGGGGGGGGGGGGkkkk..
kOOOOOkdGGGGGGGGGGGGGGOOk..
kOOOOOkdddGGGGGGGGGGGGGGk..
kOOOOOOkkkkkkkkkkkkkkkkbk..
kOOOOOOk............kbbbk..
.kOOOOOk............kbbk...
.kOOOOk.............kbbk...
.kwwOOk.............kbbk...
..kwwWk............kbbbbk..
...kkk.............kkkkkk..
"""
FOX_LEG = {"k": ("ink", 1), "O": ("fur", 5), "o": ("fur", 3.5), "w": ("cream", 3.5), "W": ("cream", 4.5),
           "e": ("ink", 0), "G": ("green", 3.6), "d": ("green", 2.2), "y": ("brass", 4.6), "b": ("wood", 2.5)}


# бобыль: яйцеподобный, клокочет под полом (вместо улитки)
BOBYL = """
....kkkk....
...kWwwwk...
..kWWwwwwk..
..kWwwwwwk..
.kwwwwwwwwk.
.kweewweewk.
.kwwwwwwwwk.
.kwwwkkwwwk.
.kwwwwwwwwk.
..kwwwwwwk..
..kkwwwwkk..
...kk..kk...
"""
BOBYL_LEG = {"k": ("ink", 1), "w": ("bone", 4.2), "W": ("bone", 5.4), "e": ("ink", 0)}

# Кокш Томик на книжной полке: лесной кот, читает с конца
TOMIK = """
.k...k...............
kxk.kxk..............
kxxkxxk..............
kxYxxYxkkkkkkkkkkk...
kxxxxxxxxxxxxxxxxxxk.
.kxxxxxxxxxxxxxxxxxxk
..kXXxxxxxxxxxxxxxxk.
..kkkkkkkkkkkkkkkkk..
"""
TOMIK_LEG = {"k": ("ink", 1), "x": ("kok", 3.6), "X": ("kok", 5), "Y": ("eye", 0)}

# Черенок Фомич: рассадный стаканчик, прутья, ростки
FOMICH = """
.....ll..LL.....
....lLLl.lLl....
.....ll.kk......
......kkddkk....
.....kddddddk...
....kuuuuuuUk...
....kuekkeuUk.l.
t...kuuuuuuUk.t.
.t..kuukkuuUkt..
..t.kkkkkkkkt...
...ttuuuuuuUk...
....kuuuuuuUk...
....kuUuuuuUk...
....kuuuuuuUk...
....kuuuuuuUk...
.....kkkkkkk....
......t...t.....
"""
FOMICH_LEG = {"k": ("ink", 1), "u": ("cream", 4.8), "U": ("cream", 3.4), "d": ("cork", 2), "e": ("ink", 0),
              "t": ("wood", 5), "l": ("plant", 5.2), "L": ("plant", 6.4)}

# Ответень Гаврилыч: гриб-дождевик на подставке, всегда уверен
GAVR = """
..kkkkk..
.kPPPPpk.
kPkPPkPpk
kPPPPPPpk
kPkkkkPpk
.kPPPPpk.
..kbbbk..
.kbbbbbk.
"""
GAVR_LEG = {"k": ("ink", 1), "P": ("parch", 5.4), "p": ("parch", 4), "b": ("wood", 4.4)}

# Уголёк Тимофеич: ходячий уголь на трёх ножках
UGOL = """
..kkkkk..
.kcfcccck
kcFckcFck
kccfccfck
kcccfccck
.kkkkkkk.
.k..k..k.
"""
UGOL_LEG = {"k": ("ink", 1), "c": ("ink", 2.2), "f": ("fire", 3), "F": ("fire", 6)}

# Оловянный ротмистр Плюмбий: половина крашеная, половина в грунте
PLUMB = """
...rr.....
..kjjjk...
..kmmmk...
..kPPzk...
..kPPzk...
.kRRmzzk..
kRRRmzzzk.
kPkRmzzkZ.
..kRmzk.Z.
..kRkzk.Z.
..kRkzk...
.kkkkkkk..
kzzzzzzzk.
.kkkkkkk..
"""
PLUMB_LEG = {"k": ("ink", 1), "r": ("red", 5.5), "j": ("tin", 1.5), "m": ("brass", 5.2), "P": ("skin", 4),
             "z": ("tin", 3.6), "Z": ("tin", 6), "R": ("red", 4.2)}

# Герой Шутливый Лисивый: клоун в ромбах, нос — скорлупа бобыля, в лапе бидон чужого смеха
LISIVY = """
...k.......k..........
..kOk.....kOk.........
..kOOk...kOOk.........
..kOwOkkkkOwOk........
.kOOOOOOOOOOOOk.......
.kwwwOOOOOOOOOk.......
.kweewOOOOkeOOk.......
.kwwwwOOOOOOOOk.......
..kwwwOOOKKKOk........
...kwwwwKKKKKk........
....kkwwwKKKk.........
...kKKKKKKKKKk........
..kKkKkKkKkKkKk.......
..kQQNNQQNNQQNk.......
.kQNNQQNNQQNNQQk......
.kNQQNNQQNNQQNQk......
kQkNNQQNNQQNNkQk......
kwkQQNNQQNNQQkwk.kkkk.
kk.NNQQNNQQNNkwkkmmmmk
...QQNNQQNNQQk..kmMmmk
...NNQQNNQQNNk..kmmmmk
...QQNNQQNNQQk..kmmmmk
...NNQQNNQQNNk..kmmmmk
...QQNNQQNNQQk..kkkkkk
...NNQQNNQQNNk........
...kQQNNkQQNNk........
....kNNk.kQQk.........
....kQQk.kNNk.........
....kbbk.kBBk.........
...kbbbk.kBBBk........
...kkkkk.kkkkk........
"""
LISIVY_LEG = {"k": ("ink", 1), "O": ("fur", 5), "w": ("bone", 5.4), "e": ("ink", 0), "K": ("bone", 5.6),
              "Q": ("brass", 3.8), "N": ("green", 3.4), "m": ("metal", 4.4), "M": ("metal", 6.4),
              "b": ("wood", 3), "B": ("red", 3.6)}

TVFOX = """
..k..............k..
.kOk............kOk.
.kOOk..........kOOk.
.kOwOkkkkkkkkkkOwOk.
.kOwwOOOOOOOOOOwwOk.
kOOOOOOOOOOOOOOOOOOk
kOOOkkkOOOOOOkkkOOOk
kOOkeWkOOOOOOkeWkOOk
kOOkeekOOOOOOkeekOOk
kOOOkkOOOOOOOOkkOOOk
kWWOOOOOOkkOOOOOOWWk
.kWWWWWWWWWWWWWWWWk.
..kWWWWWWkkWWWWWWk..
...kkWWWWWWWWWWkk...
.....kkkkkkkkkk.....
"""
TVFOX_BLINK = {6: "kOOOOOOOOOOOOOOOOOOk", 7: "kOOkkkkOOOOOOkkkkOOk", 8: "kOOOOOOOOOOOOOOOOOOk", 9: "kOOOOOOOOOOOOOOOOOOk"}
TVFOX_LEG = {"k": ("ink", 0.5), "O": ("tvfur", 5.4), "w": ("tvcream", 3), "W": ("tvcream", 4.8),
             "e": ("ink", 0), }



def soldier(c, x, base, color, flag, frame):
    c.paint(c.rect(x - 3, base - 1, x + 4, base + 1), "ink", 1, "minis")
    c.paint(c.rect(x - 2, base - 9, x + 3, base - 1), color, 3.8, "minis")
    c.px(x - 2, base - 9, color, 5, "minis")
    c.paint(c.rect(x - 1, base - 12, x + 2, base - 9), "skin", 4, "minis")
    c.paint(c.rect(x - 2, base - 13, x + 3, base - 11), "metal", 5, "minis")
    c.paint(c.line([(x + 3, base - 1), (x + 3, base - 20)]), "wood", 5, "minis")
    if flag:
        c.paint(c.poly([(x + 4, base - 20), (x + 9, base - 20), (x + 7, base - 18), (x + 9, base - 16), (x + 4, base - 16)]), color, 4.5, "minis")
    else:
        c.px(x + 3, base - 21, "metal", 6, "minis")


def gear(c, cx, cy, r, teeth, angle, obj):
    pts = []
    for i in range(teeth * 4):
        a = angle + math.tau * i / (teeth * 4)
        rr = r if (i // 2) % 2 == 0 else r - 2
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    c.paint(c.poly(pts), "brass", 4.2, obj)
    c.paint(c.ell(cx - r + 3, cy - r + 3, cx + r - 2, cy + r - 2), "brass", 5.2, obj)
    c.paint(c.ell(cx - 2, cy - 2, cx + 3, cy + 3), "brass", 1.5, obj)


def flame(c, x, y, h, rng, obj=None):
    """маленький огонёк свечи"""
    c.px(x, y, "fire", 5, obj)
    c.px(x, y - 1, "fire", 6, obj)
    if h > 1:
        c.px(x + rng.choice([-1, 0, 0, 1]) * 0 , y - 2, "fire", 7, obj)
    c.light(x, y - 1, 34, 0.32 + rng.uniform(-.04, .04))


def candle(c, x, y, h, rng, obj=None):
    c.paint(c.rect(x - 1, y - h, x + 2, y), "bone", 4.6, obj)
    c.px(x - 1, y - h, "bone", 5.5, obj)
    c.paint(c.rect(x - 2, y - 1, x + 3, y + 1), "brass", 3.8, obj)
    flame(c, x, y - h - 1, rng.integers(1, 3), rng)


# ─────────────────────────── сцена ───────────────────────────

def draw(frame):
    rng = np.random.default_rng(100 + frame)
    rs = random.Random(11)  # постоянные детали: одинаковы во всех кадрах
    c = Canvas()
    flick = [1.0, 0.9, 1.06, 0.95][frame]

    # стена: кирпичи
    wall = c.rect(0, 0, W, 214)
    c.paint(wall, "stone", 1.2)
    for row in range(0, 214 // 8 + 1):
        off = 8 if row % 2 else 0
        for col in range(-1, W // 16 + 1):
            x0, y0 = col * 16 + off, row * 8
            v = 3.3 + rs.uniform(-.6, .5)
            m = c.rect(x0 + 1, y0 + 1, x0 + 16, y0 + 8) & wall
            c.paint(m, "stone", v, tex=0.5)
            c.paint(c.rect(x0 + 1, y0 + 1, x0 + 15, y0 + 2) & wall, "stone", v + .6)
            if rs.random() < .08:
                cx = x0 + rs.randint(3, 12)
                c.paint(c.line([(cx, y0 + 2), (cx + 2, y0 + 5)]) & wall, "stone", 1.5)
    # потолок и балки
    c.paint(c.rect(0, 0, W, 16), "wood", 2.0, tex=.4)
    for x in range(0, W, 64):
        c.paint(c.rect(x + 20, 0, x + 34, 16), "wood", 3.2, tex=.4)
        c.paint(c.rect(x + 20, 14, x + 34, 16), "wood", 1.5)
    c.paint(c.rect(0, 16, W, 22), "wood", 3.4, tex=.5)
    c.paint(c.rect(0, 16, W, 17), "wood", 4.5)
    c.paint(c.rect(0, 21, W, 22), "wood", 1)
    for x in (0, 470):
        c.paint(c.rect(x, 22, x + 10, 214), "wood", 3.2, tex=.5)
        c.paint(c.rect(x + 1, 22, x + 2, 214), "wood", 4.3)
    # пол в перспективе
    floor = c.rect(0, 214, W, H)
    c.paint(floor, "wood", 3.1, tex=.6)
    vx, vy = 240, 60
    for xb in range(-360, 860, 30):
        t = (214 - vy) / (H - vy)
        xt = vx + (xb - vx) * t
        c.paint(c.line([(xt, 214), (xb, H)]) & floor, "wood", 1.2)
    for _ in range(40):
        y = rs.randint(218, H - 2)
        x = rs.randint(0, W)
        c.paint(c.line([(x, y), (x + rs.randint(4, 14), y)]) & floor, "wood", 1.6)
    c.paint(c.rect(0, 210, W, 216), "wood", 2.2)
    c.paint(c.rect(0, 210, W, 211), "wood", 4)

    # ── окно и огород ──
    frame_m = c.rect(18, 66, 92, 150) | c.ell(18, 30, 92, 104)
    c.paint(frame_m, "wood", 4.0, "garden", tex=.5)
    glass = c.rect(24, 68, 86, 146) | c.ell(24, 36, 86, 100)
    c.paint(glass, "sky", 0, "garden")
    c.lvl[glass] = np.clip((c.yy[glass] - 36) / 110 * 4.2, 0, 4)
    for sx, sy in [(30, 60), (40, 48), (64, 70), (36, 90), (78, 100), (48, 108), (70, 120), (30, 128), (58, 52)]:
        tw = (sx * 7 + frame) % 4
        c.px(sx, sy, "star", 2 if tw == 0 else 1, "garden")
    moon = c.ell(62, 50, 78, 66)
    c.paint(moon, "bone", 5.8, "garden")
    c.mat[moon] = MID["star"]
    c.lvl[moon] = 2
    c.paint(c.ell(66, 48, 82, 64) & moon, "sky", 1, "garden")
    c.paint(c.rect(54, 38, 57, 146), "wood", 4, "garden")
    c.paint(c.rect(24, 94, 86, 97), "wood", 4, "garden")
    c.paint(c.rect(12, 146, 98, 154), "wood", 5.2, "garden", tex=.5)
    c.paint(c.rect(12, 146, 98, 147), "wood", 6.3, "garden")
    c.light(55, 110, 60, 0.12)
    # кактус
    c.paint(c.poly([(22, 146), (24, 134), (36, 134), (38, 146)]), "terra", 4, "garden")
    c.paint(c.rect(22, 132, 38, 135), "terra", 5, "garden")
    c.paint(c.rect(27, 112, 33, 132), "plant", 4.3, "garden", tex=.6)
    c.paint(c.rect(23, 118, 26, 126), "plant", 4, "garden")
    c.paint(c.rect(34, 114, 37, 124), "plant", 4, "garden")
    c.paint(c.rect(26, 124, 27, 127) | c.rect(33, 122, 34, 125), "plant", 4, "garden")
    for y in range(114, 131, 3):
        c.px(28, y, "plant", 6.5, "garden")
    c.paint(c.ell(28, 108, 33, 113), "red", 6, "garden")
    # монстера
    c.paint(c.poly([(44, 146), (46, 132), (62, 132), (64, 146)]), "terra", 3.6, "garden")
    c.paint(c.rect(43, 130, 65, 133), "terra", 4.8, "garden")
    for (x0, y0, x1, y1) in [(34, 100, 52, 116), (54, 94, 74, 112), (44, 112, 60, 126), (58, 112, 74, 126), (46, 86, 60, 100)]:
        leaf = c.ell(x0, y0, x1, y1)
        c.paint(leaf, "plant", 4.4, "garden", tex=.5)
        c.paint(c.line([(x0 + 2, (y0 + y1) // 2), (x1 - 2, (y0 + y1) // 2)]) & leaf, "plant", 6)
        c.paint(c.line([((x0 + x1) // 2, y0 + 3), ((x0 + x1) // 2 + 2, y0 + 6)]) & leaf, "sky", 1)
    c.paint(c.line([(54, 131), (46, 110)]) | c.line([(54, 131), (62, 104)]) | c.line([(54, 131), (54, 94)]), "plant", 3.4, "garden")
    # Черенок Фомич вместо горшка с чили
    c.sprite(72, 129, FOMICH.strip("\n").split("\n"), FOMICH_LEG, "garden")

    # ── книжная полка ──
    c.paint(c.rect(104, 44, 174, 212), "wood", 1.5, "shelf")
    c.paint(c.rect(104, 44, 110, 212) | c.rect(168, 44, 174, 212), "wood", 4.4, "shelf", tex=.5)
    c.paint(c.rect(100, 38, 178, 45), "wood", 5.0, "shelf", tex=.4)
    c.paint(c.rect(100, 38, 178, 39), "wood", 6.2, "shelf")
    shelves = [84, 124, 164, 204]
    book_ramps = ["red", "blue", "green", "purple", "parch", "red", "blue", "brass", "green"]
    for i, sy in enumerate(shelves):
        x = 111
        while x < 164:
            w = rs.randint(3, 6)
            if x + w > 167:
                break
            h = rs.randint(24, 34)
            ramp = rs.choice(book_ramps)
            if rs.random() < .1 and x + 26 < 167:  # лежит стопкой
                for k in range(3):
                    ramp2 = rs.choice(book_ramps)
                    c.paint(c.rect(x, sy - 4 * (k + 1), x + 22 - k * 2, sy - 4 * k), ramp2, 3.6, "shelf")
                    c.paint(c.rect(x, sy - 4 * (k + 1), x + 22 - k * 2, sy - 4 * (k + 1) + 1), ramp2, 5, "shelf")
                x += 24
                continue
            c.paint(c.rect(x, sy - h, x + w, sy), ramp, 3.6, "shelf")
            c.paint(c.rect(x, sy - h, x + 1, sy), ramp, 4.8, "shelf")
            c.paint(c.rect(x + w - 1, sy - h, x + w, sy), ramp, 2.4, "shelf")
            if ramp != "brass":
                c.paint(c.rect(x, sy - h + 3, x + w, sy - h + 4) | c.rect(x, sy - 5, x + w, sy - 4), "brass", 5.2, "shelf")
            x += w + rs.choice([0, 0, 1])
        c.paint(c.rect(106, sy, 172, sy + 4), "wood", 5.0, "shelf", tex=.4)
        c.paint(c.rect(106, sy, 172, sy + 1), "wood", 6, "shelf")
    # склянка и череп
    c.paint(c.rect(155, 72, 162, 84) | c.ell(153, 70, 164, 80), "glass", 4, "shelf")
    c.paint(c.ell(155, 74, 162, 81), "brew", 3, "shelf")
    c.paint(c.rect(157, 66, 160, 71), "cork", 4, "shelf")
    c.paint(c.ell(112, 24, 128, 40), "bone", 4.4, "shelf")
    c.paint(c.rect(114, 34, 126, 39), "bone", 4, "shelf")
    c.paint(c.rect(115, 30, 118, 33) | c.rect(122, 30, 125, 33), "ink", 0, "shelf")
    c.paint(c.rect(119, 35, 121, 37), "ink", 0, "shelf")
    for x in (116, 119, 122, 125):
        c.px(x, 38, "ink", 1, "shelf")
    candle(c, 164, 38, 10, rng, "shelf")

    # ── очаг ──
    hearth = c.rect(186, 94, 294, 212)
    c.paint(hearth, "grey", 3.4, "hearth", tex=.6)
    for row in range(94, 212, 9):
        off = 7 if (row // 9) % 2 else 0
        c.paint(c.rect(186, row, 294, row + 1), "grey", 1.4)
        for x in range(186 + off, 294, 14):
            c.paint(c.rect(x, row, x + 1, row + 9) & hearth, "grey", 1.4)
            c.paint(c.rect(x + 1, row + 1, x + 13, row + 2) & hearth, "grey", 4.4)
    opening = c.rect(202, 150, 278, 212) | c.ell(202, 112, 278, 188)
    c.paint(opening, "ink", 0.6, "hearth")
    inner = c.rect(210, 158, 270, 206) | c.ell(210, 124, 270, 192)
    c.paint(inner, "stone", 1.4, "hearth", tex=.6)
    for row in range(126, 206, 6):
        c.paint(c.rect(210, row, 270, row + 1) & inner, "stone", 0.4)
    c.paint(c.rect(178, 86, 302, 95), "wood", 4.8, "hearth", tex=.4)
    c.paint(c.rect(178, 86, 302, 87), "wood", 6.2, "hearth")
    c.paint(c.rect(178, 94, 302, 95), "wood", 2, "hearth")
    # поленья
    c.paint(c.line([(214, 205), (262, 198)], 5), "wood", 3.6, "hearth")
    c.paint(c.line([(220, 199), (266, 206)], 5), "wood", 3.0, "hearth")
    c.paint(c.ell(260, 195, 268, 203), "wood", 5.5, "hearth")
    # огонь
    fire_rng = np.random.default_rng(7 + frame * 13)
    tongues = [(222, 22), (231, 34), (240, 44), (249, 36), (258, 24), (236, 30), (245, 28)]
    for tx, th in tongues:
        th = int(th * fire_rng.uniform(.8, 1.15))
        sway = fire_rng.integers(-3, 4)
        pts = [(tx - 7, 202), (tx + 7, 202), (tx + 2 + sway, 202 - th), (tx - 1 + sway, 202 - th + 2)]
        m = c.poly(pts)
        c.paint(m, "fire", 0, "hearth")
        c.lvl[m] = np.clip(1.5 + (c.yy[m] - (202 - th)) / th * 5.5 - np.abs(c.xx[m] - tx) / 6, 1, 7)
    for _ in range(6):
        ex, ey = int(fire_rng.integers(218, 262)), int(fire_rng.integers(148, 176))
        c.px(ex, ey, "fire", 5, "hearth")
    c.light(240, 188, 300, 1.05 * flick)
    c.light(240, 196, 70, 0.5 * flick)
    # котёл
    for y in range(114, 146, 2):
        c.px(240, y, "metal", 3.5 if y % 4 else 2, "hearth")
    pot = c.poly([(226, 150), (254, 150), (252, 162), (246, 168), (234, 168), (228, 162)])
    c.paint(pot, "metal", 2.4, "hearth", tex=.4)
    c.paint(c.rect(224, 148, 256, 152), "metal", 3.6, "hearth")
    c.paint(c.ell(227, 146, 253, 151), "brew", 3.2, "hearth")
    for i, bx in enumerate((233, 241, 247)):
        if (frame + i) % 3 != 0:
            c.px(bx, 146 - (frame + i) % 3, "brew", 5, "hearth")
    # щит и предметы на каминной полке
    shield = c.poly([(226, 50), (254, 50), (254, 66), (240, 80), (226, 66)])
    c.paint(shield, "red", 3.8, "hearth", tex=.3)
    c.paint(c.rect(238, 52, 242, 76) & shield, "brass", 5.4, "hearth")
    c.paint(c.rect(228, 60, 252, 64) & shield, "brass", 5.4, "hearth")
    c.paint(c.line([(226, 50), (254, 50)]), "brass", 4.5, "hearth")
    c.paint(c.poly([(190, 72), (200, 72), (196, 79), (200, 86), (190, 86), (194, 79)]), "glass", 5, "hearth")
    c.paint(c.rect(189, 70, 201, 72) | c.rect(189, 86, 201, 87), "wood", 5, "hearth")
    c.paint(c.rect(193, 82, 198, 86), "parch", 6, "hearth")
    c.paint(c.rect(276, 74, 288, 86), "metal", 4, "hearth")
    c.paint(c.rect(288, 76, 291, 84), "metal", 3, "hearth")
    c.paint(c.rect(276, 72, 288, 75), "cream", 5, "hearth")

    # ── доска объявлений ──
    c.paint(c.rect(302, 30, 362, 70), "wood", 4.4, "board", tex=.4)
    c.paint(c.rect(305, 33, 359, 67), "cork", 3.6, "board", tex=.8)
    for (x0, y0, x1, y1, lines) in [(309, 36, 327, 56, 5), (331, 35, 355, 50, 3), (318, 52, 348, 65, 2)]:
        c.paint(c.rect(x0, y0, x1, y1), "parch", 5.6, "board")
        for k in range(lines):
            ly = y0 + 3 + k * 3
            c.paint(c.rect(x0 + 2, ly, x1 - 2 - rs.randint(0, 5), ly + 1), "parch", 2.4, "board")
        c.px((x0 + x1) // 2, y0 + 1, "red", 5, "board")
    c.paint(c.ell(334, 38, 344, 46), "glass", 5, "board")   # «телеграм»-кружок
    c.paint(c.poly([(336, 42), (342, 39), (340, 44)]), "cream", 5, "board")

    # ── келья ИИ: стол алхимика ──
    ang = frame * math.tau / 40
    gear(c, 312, 90, 11, 8, ang, "ai")
    gear(c, 329, 104, 7, 6, -ang * 1.5 + .2, "ai")
    gear(c, 305, 110, 6, 5, ang * 2, "ai")
    # магическое зеркало: лис в экране
    c.paint(c.rect(336, 102, 372, 150), "brass", 4.4, "screen", tex=.4)
    c.paint(c.ell(342, 92, 366, 112), "brass", 4.4, "screen")
    c.paint(c.ell(351, 95, 357, 101), "red", 5, "screen")
    screen = c.rect(340, 108, 368, 146)
    c.paint(screen, "screen", 1.0, "screen")
    c.lvl[screen] = np.where(c.yy[screen] % 2 == 0, 1.6, 0.8)
    rows = TVFOX.strip("\n").split("\n")
    if frame == 2:
        rows = [TVFOX_BLINK.get(i, row) for i, row in enumerate(rows)]
    c.sprite(344, 118 + (1 if frame % 2 else 0), rows, TVFOX_LEG, "screen")
    for x in range(342, 367, 3):   # полоса помех
        c.px(x + frame, 111 + frame * 8, "screen", 6, "screen")
    c.light(354, 128, 44, 0.22)
    # стол
    c.paint(c.rect(296, 156, 378, 163), "wood", 5.0, "ai", tex=.4)
    c.paint(c.rect(296, 156, 378, 157), "wood", 6.3, "ai")
    c.paint(c.rect(300, 163, 305, 212) | c.rect(369, 163, 374, 212), "wood", 3.4, "ai", tex=.4)
    c.paint(c.rect(305, 164, 369, 172), "wood", 3.8, "ai")
    c.paint(c.rect(334, 166, 340, 169), "brass", 5, "ai")
    c.paint(c.rect(336, 150, 372, 156), "wood", 4.2, "screen")
    # шар
    c.paint(c.poly([(308, 156), (310, 150), (326, 150), (328, 156)]), "brass", 3.8, "ai")
    orb = c.ell(305, 127, 332, 153)
    c.paint(orb, "orb", 0, "ai")
    d = np.sqrt((c.xx[orb] - 314) ** 2 + (c.yy[orb] - 135) ** 2)
    c.lvl[orb] = np.clip(6.4 - d / 3.2, 1.2, 7)
    ex = 318 + [0, -3, 0, 3][frame]
    c.paint(c.ell(ex - 5, 137, ex + 6, 144), "cream", 5.2, "ai")
    c.paint(c.rect(ex - 1, 138, ex + 2, 143), "ink", 0, "ai")
    c.px(310, 132, "orb", 7, "ai")
    c.px(311, 131, "orb", 7, "ai")
    c.light(318, 140, 70, 0.28)
    # свиток, чернильница, перо
    c.sprite(296, 148, GAVR.strip("\n").split("\n"), GAVR_LEG, "ai")      # Ответень Гаврилыч
    c.paint(c.rect(295, 139, 306, 144), "parch", 6, "ai")                     # табличка над ним
    c.paint(c.rect(297, 141, 304, 142), "parch", 2.4, "ai")
    c.px(300, 145, "wood", 4, "ai")
    c.paint(c.rect(374, 148, 379, 156), "ink", 1.5, "ai")
    c.paint(c.line([(376, 150), (384, 136)], 2), "cream", 5, "ai")
    candle(c, 330, 156, 7, rng, "ai")

    # ── оружейная: шкаф ──
    c.paint(c.rect(380, 64, 462, 212), "wood", 4.0, "minis", tex=.5)
    c.paint(c.rect(374, 56, 468, 65), "wood", 5.0, "minis", tex=.4)
    c.paint(c.rect(374, 56, 468, 57), "wood", 6.2, "minis")
    c.paint(c.rect(386, 70, 456, 206), "wood", 0.8, "minis")
    for sy in (110, 150, 190):
        c.paint(c.rect(384, sy, 458, sy + 3), "wood", 5.0, "minis")
    colors = ["green", "red", "blue", "green", "red", "purple", "blue"]
    for si, sy in enumerate((110, 150, 190)):
        for k in range(6):
            x = 392 + k * 11
            soldier(c, x, sy - 1, colors[(k + si * 2) % len(colors)], (k + si) % 2 == 0, frame)
    c.paint(c.rect(420, 70, 423, 206), "wood", 4.4, "minis")
    c.paint(c.rect(415, 128, 418, 132) | c.rect(425, 128, 428, 132), "brass", 5.5, "minis")
    helm = c.ell(404, 34, 432, 62) & c.rect(404, 34, 432, 57)
    c.paint(helm, "metal", 4.2, "minis", tex=.4)
    c.paint(c.rect(417, 34, 419, 57), "metal", 6, "minis")
    c.paint(c.rect(408, 46, 428, 48), "ink", 0.5, "minis")
    c.paint(c.poly([(418, 36), (426, 26), (436, 28), (430, 34), (422, 38)]), "red", 4.6, "minis")

    # ── люстра ──
    for y in range(22, 36, 2):
        c.px(240, y, "metal", 3, "chandelier")
    ring = c.ell(208, 36, 272, 46) & ~c.ell(212, 38, 268, 44)
    c.paint(ring, "metal", 2.8, "chandelier")
    c.paint(c.line([(240, 34), (212, 40)]) | c.line([(240, 34), (268, 40)]), "metal", 2.5, "chandelier")
    for x in (212, 226, 254, 268):
        candle(c, x, 40 if x in (212, 268) else 44, 6, rng, "chandelier")

    # ── передний план: бочка с костями, картами и лютней (конец недели) ──
    barrel = c.poly([(404, 278), (398, 254), (398, 236), (404, 214), (452, 214), (458, 236), (458, 254), (452, 278)])
    c.paint(barrel, "wood", 3.6, "barrel", tex=.5)
    for x in range(406, 452, 9):
        c.paint(c.rect(x, 214, x + 1, 278) & barrel, "wood", 2)
    for y in (222, 266):
        c.paint(c.rect(396, y, 460, y + 4) & c.rect(396, 210, 460, 280), "metal", 3, "barrel")
    c.paint(c.ell(402, 208, 454, 220), "wood", 5.2, "barrel")
    # кости
    for (dx, dy, pips) in ((410, 202, [(2, 2), (5, 5)]), (419, 205, [(2, 2), (4, 4), (6, 2), (2, 6), (6, 6)])):
        c.paint(c.rect(dx, dy, dx + 9, dy + 9), "bone", 5.2, "barrel")
        c.paint(c.rect(dx, dy + 8, dx + 9, dy + 9), "bone", 3.5, "barrel")
        for (px_, py_) in pips:
            c.px(dx + px_, dy + py_, "ink", 0, "barrel")
    # карты веером
    for k, (cx_, cy_) in enumerate(((432, 206), (437, 204), (442, 206))):
        c.paint(c.rect(cx_, cy_, cx_ + 8, cy_ + 11), "parch", 6.2 - k * .4, "barrel")
        c.px(cx_ + 3, cy_ + 4, "red" if k != 1 else "ink", 5 if k != 1 else 0, "barrel")
        c.px(cx_ + 4, cy_ + 5, "red" if k != 1 else "ink", 5 if k != 1 else 0, "barrel")
    # лютня, прислонённая к бочке
    c.paint(c.line([(392, 240), (404, 196)], 3), "wood", 2.6, "barrel")
    c.paint(c.poly([(401, 198), (407, 188), (411, 190), (405, 200)]), "wood", 3.2, "barrel")
    lute = c.ell(378, 234, 402, 266)
    c.paint(lute, "wood", 5.6, "barrel", tex=.3)
    c.paint(c.ell(380, 236, 400, 262) & ~c.ell(382, 238, 402, 266), "wood", 7, "barrel")
    c.paint(c.ell(386, 244, 394, 252), "ink", 0.5, "barrel")
    c.paint(c.rect(385, 256, 396, 258), "wood", 2, "barrel")
    c.paint(c.line([(390, 256), (403, 197)]), "bone", 5.5, "barrel")

    # ── Уголёк Тимофеич у очага ──
    c.sprite(280, 203, UGOL.strip("\n").split("\n"), UGOL_LEG, "hearth")
    # ── Кокш Томик на книжной полке ──
    c.sprite(132, 30, TOMIK.strip("\n").split("\n"), TOMIK_LEG, "shelf")
    z = [(152, 26), (154, 22), (156, 18), (158, 14)][frame]
    c.px(z[0], z[1], "cream", 3.6)
    c.px(z[0] + 1, z[1], "cream", 3.6)
    c.px(z[0], z[1] + 1, "cream", 3.6)
    c.px(z[0] + 1, z[1] + 2, "cream", 3.6)
    # ── Плюмбий объявляет манёвры на каминной полке ──
    c.sprite(206, 72, PLUMB.strip("\n").split("\n"), PLUMB_LEG, "plumbiy")
    # ── бобыль из-под пола и Герой Шутливый Лисивый с бидоном ──
    c.sprite(304 + (1 if frame % 2 else 0), 266, BOBYL.strip("\n").split("\n"), BOBYL_LEG, "snail")
    if frame % 2:
        c.paint(c.line([(318, 262), (321, 259)]) | c.line([(318, 266), (322, 266)]), "bone", 5.5)
    c.sprite(344, 246, LISIVY.strip("\n").split("\n"), LISIVY_LEG, "barrel")
    c.light(356, 256, 46, 0.22)

    # ── дымная горница: стол с кальяном и лис ──
    c.paint(c.rect(138, 232, 146, 266), "wood", 3.4, "table", tex=.4)
    c.paint(c.ell(122, 262, 162, 272), "wood", 3.2, "table")
    c.paint(c.ell(90, 222, 194, 238), "wood", 4.4, "table", tex=.5)
    c.paint(c.ell(92, 222, 192, 234), "wood", 5.4, "table", tex=.5)
    # кальян
    flask = c.ell(128, 202, 154, 228)
    c.paint(flask, "glass", 3.6, "hookah")
    c.paint(c.ell(131, 214, 151, 227) & flask, "glass", 2.6, "hookah")
    c.paint(c.line([(133, 207), (136, 205)]), "glass", 6.5, "hookah")
    for i, (bx, by) in enumerate([(138, 222), (144, 218), (140, 214)]):
        if (frame + i) % 2 == 0:
            c.px(bx, by - frame % 2, "glass", 6.5, "hookah")
    c.paint(c.rect(139, 168, 144, 204), "brass", 4.6, "hookah")
    c.paint(c.rect(139, 168, 140, 204), "brass", 6, "hookah")
    c.paint(c.ell(132, 176, 151, 181), "brass", 4.2, "hookah")
    c.paint(c.rect(136, 188, 147, 191), "brass", 3.6, "hookah")
    c.paint(c.poly([(135, 168), (148, 168), (146, 160), (137, 160)]), "terra", 4.4, "hookah")
    c.paint(c.rect(133, 157, 150, 161), "metal", 5, "hookah")
    c.paint(c.ell(134, 153, 150, 159), "metal", 5.6, "hookah")
    for i, cx_ in enumerate((136, 140, 144)):
        c.paint(c.rect(cx_, 154, cx_ + 4, 157), "fire", 2.5 + ((frame + i) % 3), "hookah")
        c.px(cx_ + 1, 154, "fire", 5 + (frame + i) % 2, "hookah")
    c.light(141, 155, 36, 0.3)
    # шланг к лису
    hose = [(148, 186), (156, 196), (158, 210), (150, 219)]
    hose2 = [(137, 192), (122, 200), (106, 214), (90, 227)]
    c.paint(c.line(hose2, 3), "green", 2.6, "hookah")
    c.paint(c.line(hose2, 1), "green", 4.2, "hookah")
    # кружка
    c.paint(c.rect(104, 214, 114, 226), "metal", 4, "table")
    c.paint(c.rect(114, 216, 117, 223), "metal", 3, "table")
    c.paint(c.rect(104, 212, 114, 215), "cream", 5, "table")
    # табурет и лис
    c.paint(c.rect(56, 238, 94, 243), "wood", 4.6, "fox")
    c.paint(c.rect(60, 243, 64, 272) | c.rect(86, 243, 90, 272), "wood", 3.4, "fox")
    c.sprite(64, 210, FOX.strip("\n").split("\n"), FOX_LEG, "fox")
    # дым колечками
    for k in range(3):
        t = ((frame + k * 1.33) % 4) / 4
        sx = int(140 - 6 * t + (k - 1) * 3)
        sy = int(150 - 40 * t)
        r = 2 + int(4 * t)
        ring = c.ell(sx - r, sy - r // 2 - 1, sx + r + 1, sy + r // 2 + 1)
        if r > 3:
            ring &= ~c.ell(sx - r + 2, sy - r // 2 + 1, sx + r - 1, sy + r // 2)
        c.paint(ring & (c.obj == 0), "smoke", 3.4 - t * 2)
    # дым у лиса
    t = frame / 4
    for k in range(2):
        mx, my = int(92 + 4 * t + k * 5), int(214 - 16 * t - k * 7)
        c.paint(c.ell(mx - 2, my - 2, mx + 3, my + 2) & (c.obj != OBJ["fox"]), "smoke", 3 - t * 1.5)
    return c


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames, last = [], None
    for f in range(4):
        c = draw(f)
        frames.append(c.render())
        last = c
    sheet = np.concatenate(frames, axis=1)
    Image.fromarray(sheet).quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(OUT / "frames.png", optimize=True)

    # подсветки и координаты предметов
    hot = {}
    for room, parts in HOT.items():
        mask = np.isin(last.obj, [OBJ[p] for p in parts])
        grow = mask.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            grow |= np.roll(np.roll(mask, dy, 0), dx, 1)
        grow2 = grow.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            grow2 |= np.roll(np.roll(grow, dy, 0), dx, 1)
        rgba = np.zeros((H, W, 4), np.uint8)
        rgba[grow2 & ~grow] = (24, 20, 37, 255)
        rgba[grow & ~mask] = (254, 231, 97, 255)
        Image.fromarray(rgba).save(OUT / f"hl-{room}.png", optimize=True)
        ys, xs = np.nonzero(mask)
        hot[room] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    (SRC / "hotspots.json").write_text(json.dumps({"size": [W, H], "hot": hot}, indent=1), encoding="utf-8")

    # иконки комнат — вырезки из первого кадра
    img = Image.fromarray(frames[0])
    crops = {"garden": (16, 70, 100, 154), "shelf": (98, 22, 180, 104), "hookah": (60, 150, 170, 260),
             "ai": (294, 78, 336, 162), "minis": (382, 68, 460, 146), "thoughts": (192, 108, 288, 204),
             "search": (300, 28, 364, 72), "anime": (330, 88, 378, 156), "games": (374, 184, 462, 280)}
    for k, box in crops.items():
        im = img.crop(box)
        s = 4 if max(im.size) < 100 else 3
        im.resize((im.width * s, im.height * s), Image.NEAREST).save(OUT / f"icon-{k}.png", optimize=True)
    # отдельный оловянный воин на прозрачном фоне — заглушка для миниатюр без фото
    c = Canvas()
    c.mat[:] = 0
    c.paint(c.ell(10, 36, 26, 40), "ink", 1, "minis")
    soldier(c, 16, 37, "metal", True, 0)
    c.light(8, 10, 60, 0.9)
    rgb = c.render(ambient=0.5)
    alpha = np.where(c.obj > 0, 255, 0).astype(np.uint8)
    icon = np.dstack([rgb, alpha])[12:42, 8:28]
    Image.fromarray(icon, "RGBA").resize((20 * 6, 30 * 6), Image.NEAREST).save(OUT / "icon-soldier.png", optimize=True)
    print("зал нарисован:", OUT)


if __name__ == "__main__":
    main()
