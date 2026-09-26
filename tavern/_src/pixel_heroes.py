#!/usr/bin/env python3
"""Пиксельные портреты героев Лисьей таверны и неоновые текстуры для оформления.

  assets/heroes/<id>.png      — портреты 32×32 (CSS увеличивает их без размытия)
  assets/heroes/orb-<id>.png  — «зеркала» комнат для орбиты в общем зале
  assets/heroes/moss.png      — вертикально бесшовная грибница для боковых колонн

Нужны Pillow и numpy (pip install pillow numpy). Запуск: python tavern/_src/pixel_heroes.py
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SRC = Path(__file__).resolve().parent
OUT = SRC.parent / "assets" / "heroes"
S = 32

PAL = {
    "k": "#0b0806",
    # лисий мех
    "O": "#c4551f", "o": "#8d3b16", "H": "#e07a3a", "i": "#3a1a10",
    "w": "#e8dcc6", "W": "#bcbfa9",
    "e": "#6fc9bd", "E": "#140f0b",
    # стёганка, фартук, мундштуки
    "G": "#2f4a35", "g": "#1f3326", "q": "#46654b",
    "a": "#8e9a90", "A": "#6b776d",
    "m": "#d49f3e", "M": "#fff0a8",
    # огонь и дым
    "f": "#e2662a", "F": "#ffd259", "r": "#a8231a", "s": "#6fc9bd", "S": "#b9f2e8",
    # уголь
    "c": "#1d1a1c", "C": "#38323a",
    # прутья, стаканчик, земля, листья
    "t": "#6e4a2a", "T": "#9a6b3c", "u": "#d8e4e6", "U": "#a9bfc4", "d": "#3a2616",
    "l": "#69a33c", "L": "#96c858", "n": "#31662a",
    # гриб
    "p": "#c9a77a", "P": "#e6cfa4", "b": "#8a6a45", "B": "#5e4630",
    # кокш
    "x": "#4a5550", "X": "#6f7d76", "y": "#2c3431", "Y": "#e6ff3a",
    # книга
    "v": "#7a1f2a", "V": "#f2e6c8",
    # олово и мундир
    "z": "#8d97aa", "Z": "#b8c0ce", "j": "#4a4e60", "R": "#9e2528", "h": "#c33c33",
    # клоун
    "Q": "#b88a2a", "N": "#56663a", "K": "#f7f2e4",
    # сетка Осевого
    "I": "#e6ff3a", "J": "#6d7a1a", "D": "#141a14", "Ω": "#ff3fb4",
}
KEYS = list(PAL)
IDX = {k: i + 1 for i, k in enumerate(KEYS)}
RGB = {IDX[k]: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in PAL.items()}


class Pix:
    def __init__(self, w=S, h=S):
        self.w, self.h = w, h
        self.a = np.zeros((h, w), np.int16)

    def _m(self, fn):
        im = Image.new("1", (self.w, self.h))
        fn(ImageDraw.Draw(im))
        return np.array(im, bool)

    def poly(self, pts, c):
        self.a[self._m(lambda d: d.polygon(pts, fill=1))] = IDX[c]

    def rect(self, x0, y0, x1, y1, c):
        self.a[y0:y1 + 1, x0:x1 + 1] = IDX[c]

    def ell(self, x0, y0, x1, y1, c):
        self.a[self._m(lambda d: d.ellipse([x0, y0, x1, y1], fill=1))] = IDX[c]

    def line(self, pts, c, w=1):
        self.a[self._m(lambda d: d.line(pts, fill=1, width=w))] = IDX[c]

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = IDX[c]

    def pxs(self, pts, c):
        for x, y in pts:
            self.px(x, y, c)

    def outline(self):
        filled = self.a > 0
        pad = np.pad(filled, 1)
        grow = pad[1:-1, 1:-1] | pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
        self.a[grow & ~filled] = IDX["k"]

    def image(self):
        out = np.zeros((self.h, self.w, 4), np.uint8)
        for i, rgb in RGB.items():
            out[self.a == i] = (*rgb, 255)
        return Image.fromarray(out, "RGBA")


def fox_head(p, cx=16, top=3, ears=True):
    """Лисья морда по мотивам лого таверны: треугольные уши, светлые щёки, бирюзовые глаза."""
    if ears:
        p.poly([(cx - 11, top), (cx - 4, top + 8), (cx - 12, top + 10)], "o")
        p.poly([(cx - 10, top + 3), (cx - 5, top + 8), (cx - 10, top + 8)], "i")
        p.poly([(cx + 11, top), (cx + 12, top + 10), (cx + 4, top + 8)], "O")
        p.poly([(cx + 10, top + 3), (cx + 10, top + 8), (cx + 5, top + 8)], "i")
    p.poly([(cx - 12, top + 9), (cx, top + 5), (cx + 12, top + 9), (cx + 10, top + 15), (cx, top + 17), (cx - 10, top + 15)], "O")
    p.poly([(cx, top + 5), (cx + 12, top + 9), (cx + 10, top + 15), (cx, top + 12)], "o")
    p.poly([(cx - 12, top + 9), (cx - 4, top + 7), (cx - 9, top + 13)], "H")
    # щёки и морда
    p.poly([(cx - 10, top + 14), (cx, top + 12), (cx - 3, top + 20)], "w")
    p.poly([(cx + 10, top + 14), (cx, top + 12), (cx + 3, top + 20)], "W")
    p.poly([(cx - 3, top + 17), (cx + 3, top + 17), (cx, top + 21)], "w")
    p.rect(cx - 1, top + 19, cx, top + 20, "E")
    # глаза
    p.pxs([(cx - 6, top + 10), (cx - 5, top + 10), (cx - 4, top + 11)], "E")
    p.pxs([(cx + 6, top + 10), (cx + 5, top + 10), (cx + 4, top + 11)], "E")
    p.px(cx - 5, top + 10, "e")
    p.px(cx + 5, top + 10, "e")


def kalyanych():
    p = Pix()
    # хвост с тлеющим кончиком и дымом
    p.poly([(24, 31), (29, 22), (31, 18), (30, 26), (27, 31)], "O")
    p.poly([(29, 18), (31, 15), (31, 20)], "w")
    p.pxs([(30, 14), (31, 14), (30, 13)], "f")
    p.px(31, 13, "F")
    p.pxs([(29, 11), (28, 10), (29, 9), (30, 8), (29, 6), (28, 5)], "s")
    p.pxs([(30, 10), (29, 7)], "S")
    # плечи: стёганка
    p.poly([(4, 31), (6, 25), (11, 22), (21, 22), (26, 25), (28, 31)], "G")
    for y in (25, 28):
        p.line([(6, y), (26, y)], "g")
    for x in (9, 14, 19, 24):
        p.line([(x, 23), (x, 31)], "g")
    # фартук из клеёнки
    p.poly([(10, 31), (11, 24), (21, 24), (22, 31)], "a")
    for x in range(11, 22, 3):
        p.line([(x, 25), (x, 31)], "A")
    p.line([(11, 24), (8, 22)], "A")
    p.line([(21, 24), (24, 22)], "A")
    # связка мундштуков
    for i, x in enumerate(range(9, 24, 2)):
        y = 22 + (1 if 11 <= x <= 21 else 0) + (1 if 13 <= x <= 19 else 0)
        p.px(x, y, "m" if i % 2 else "M")
        p.px(x, y + 1, "m")
    fox_head(p, 16, 2)
    p.outline()
    # тлеющий кончик светится поверх контура
    p.px(31, 13, "F")
    return p


def lisivy():
    p = Pix()
    # балахон в ромб
    p.poly([(2, 31), (5, 24), (11, 21), (21, 21), (27, 24), (30, 31)], "Q")
    for x0 in range(-4, 34, 6):
        for y0 in (22, 28):
            p.poly([(x0 + 3, y0), (x0 + 6, y0 + 3), (x0 + 3, y0 + 6), (x0, y0 + 3)], "N")
    p.a[:21, :] = 0
    # жабо из марли
    for i, x in enumerate(range(7, 26, 3)):
        p.ell(x - 2, 19, x + 2, 23, "K" if i % 2 else "V")
    # бубенцы, набитые мхом
    p.ell(4, 27, 6, 29, "m")
    p.px(5, 28, "n")
    p.ell(25, 27, 27, 29, "m")
    p.px(26, 28, "n")
    fox_head(p, 16, 1)
    # мел и сажа: левая щека белая, правая стёрлась
    p.poly([(6, 9), (12, 9), (12, 14), (7, 15)], "K")
    p.pxs([(10, 11), (11, 11), (12, 12)], "E")
    p.px(11, 11, "e")
    p.line([(9, 8), (12, 7)], "E")
    p.pxs([(20, 13), (22, 14), (21, 15)], "c")
    # нос — скорлупа бобыля
    p.ell(12, 15, 20, 22, "E")
    p.ell(13, 16, 19, 21, "K")
    p.pxs([(14, 17), (15, 17)], "S")
    p.line([(14, 20), (18, 19)], "U")
    p.outline()
    return p


def ugolek():
    p = Pix()
    # жаровня
    p.poly([(3, 31), (6, 26), (26, 26), (29, 31)], "B")
    p.line([(4, 27), (28, 27)], "b")
    for x in range(6, 27, 4):
        p.px(x, 29, "f")
        p.px(x + 1, 30, "r")
    # сам уголь
    p.poly([(7, 18), (9, 10), (15, 6), (22, 8), (26, 15), (24, 21), (16, 23), (9, 22)], "c")
    p.poly([(15, 6), (22, 8), (26, 15), (19, 12)], "C")
    for pts in ([(10, 12), (13, 15), (12, 19)], [(21, 10), (19, 14), (22, 18)], [(14, 20), (17, 18), (20, 21)]):
        p.line(pts, "r")
    for x, y in ((13, 15), (19, 14), (17, 18)):
        p.px(x, y, "f")
    # глаза-угольки
    p.rect(12, 12, 13, 13, "F")
    p.rect(18, 12, 19, 13, "F")
    p.px(13, 13, "M")
    p.px(19, 13, "M")
    # три ножки
    for x0, x1 in ((10, 8), (16, 16), (22, 24)):
        p.line([(x0, 22), (x1, 26)], "c")
    p.outline()
    # искры над жаровней
    p.pxs([(6, 5), (27, 3), (24, 1)], "F")
    p.px(5, 3, "f")
    return p


def fomich():
    p = Pix()
    # рассадный стаканчик-туловище
    p.poly([(9, 31), (8, 18), (24, 18), (23, 31)], "u")
    p.poly([(19, 18), (24, 18), (23, 31), (20, 31)], "U")
    p.rect(8, 18, 24, 19, "d")
    p.line([(10, 26), (22, 26)], "U")
    # прутья-руки, подвязанные бечёвкой
    p.line([(8, 22), (3, 17), (2, 12)], "t", 1)
    p.line([(3, 17), (1, 18)], "t")
    p.line([(24, 22), (29, 16), (30, 11)], "t", 1)
    p.line([(29, 16), (31, 17)], "T")
    p.pxs([(5, 19), (27, 18)], "P")
    p.ell(0, 9, 3, 12, "l")
    # голова — ещё один стаканчик с землёй и ростками
    p.poly([(10, 17), (9, 8), (23, 8), (22, 17)], "u")
    p.poly([(19, 8), (23, 8), (22, 17), (19, 17)], "U")
    p.rect(9, 8, 23, 9, "d")
    p.line([(16, 8), (16, 3)], "n")
    p.line([(13, 8), (11, 4)], "n")
    p.ell(15, 0, 21, 4, "l")
    p.ell(8, 2, 13, 5, "L")
    p.px(18, 2, "L")
    # лицо
    p.rect(12, 12, 13, 13, "E")
    p.rect(18, 12, 19, 13, "E")
    p.px(12, 12, "S")
    p.px(18, 12, "S")
    p.line([(14, 15), (17, 15)], "B")
    # ноги-черенки
    p.line([(12, 31), (12, 29)], "t")
    p.line([(20, 31), (20, 29)], "t")
    p.outline()
    return p


def gavrilych():
    p = Pix()
    # табличка
    p.rect(8, 0, 23, 5, "V")
    p.line([(10, 2), (21, 2)], "B")
    p.line([(10, 4), (17, 4)], "B")
    p.line([(15, 6), (15, 7)], "t")
    # подставка
    p.poly([(7, 31), (10, 26), (22, 26), (25, 31)], "t")
    p.line([(8, 30), (24, 30)], "T")
    # гриб-дождевик
    p.ell(6, 8, 26, 27, "p")
    p.ell(14, 8, 26, 24, "b")
    p.ell(7, 9, 20, 20, "P")
    for x, y in ((10, 12), (14, 10), (18, 13), (9, 17), (21, 11), (23, 17), (13, 22), (20, 21)):
        p.px(x, y, "B")
    # уверенное лицо
    p.line([(10, 13), (13, 12)], "E")
    p.line([(18, 12), (21, 13)], "E")
    p.rect(11, 15, 12, 16, "E")
    p.rect(19, 15, 20, 16, "E")
    p.poly([(12, 20), (20, 20), (18, 23), (14, 23)], "E")
    p.line([(13, 21), (19, 21)], "r")
    p.outline()
    return p


def tomik():
    p = Pix()
    # раскрытая книга
    p.poly([(1, 31), (3, 25), (15, 27), (16, 31)], "V")
    p.poly([(16, 31), (17, 27), (29, 25), (31, 31)], "V")
    p.line([(16, 27), (16, 31)], "v")
    for y in (28, 30):
        p.line([(4, y - 1), (13, y)], "W")
        p.line([(19, y), (28, y - 1)], "W")
    p.rect(1, 31, 31, 31, "v")
    # кокш: лесной кот
    p.ell(7, 13, 25, 29, "x")
    p.ell(9, 15, 17, 27, "X")
    p.poly([(7, 11), (8, 2), (14, 7)], "x")
    p.poly([(25, 11), (24, 2), (18, 7)], "x")
    p.px(9, 5, "X")
    p.px(23, 5, "X")
    p.ell(6, 5, 26, 20, "x")
    p.ell(8, 7, 18, 18, "X")
    # глаза: читает с конца
    p.rect(10, 11, 12, 13, "Y")
    p.rect(20, 11, 22, 13, "Y")
    p.line([(11, 11), (11, 13)], "E")
    p.line([(21, 11), (21, 13)], "E")
    p.pxs([(15, 15), (16, 15), (15, 16)], "i")
    p.line([(13, 17), (15, 16)], "y")
    p.line([(17, 16), (19, 17)], "y")
    # усы
    p.line([(3, 15), (9, 16)], "W")
    p.line([(23, 16), (29, 15)], "W")
    # хвост
    p.line([(24, 26), (29, 22), (30, 17)], "x", 2)
    p.outline()
    return p


def plumbiy():
    p = Pix()
    # подставка
    p.ell(6, 27, 26, 31, "j")
    p.ell(7, 27, 25, 29, "z")
    # мундир: левая половина крашеная, правая в сером грунте
    p.poly([(7, 27), (8, 16), (16, 14), (16, 27)], "R")
    p.poly([(16, 14), (24, 16), (25, 27), (16, 27)], "z")
    p.line([(16, 15), (16, 26)], "m")
    p.pxs([(14, 18), (14, 21), (14, 24)], "m")
    p.pxs([(18, 18), (18, 21), (18, 24)], "Z")
    p.poly([(5, 17), (9, 15), (10, 18), (5, 19)], "m")      # эполет золотой
    p.poly([(27, 17), (23, 15), (22, 18), (27, 19)], "Z")   # эполет в грунте
    p.line([(8, 19), (5, 26)], "R", 2)
    p.line([(24, 19), (27, 26)], "z", 2)
    # сабля
    p.line([(28, 27), (30, 12)], "Z")
    p.px(29, 26, "m")
    # голова
    p.ell(11, 6, 21, 15, "Z")
    p.poly([(16, 6), (21, 8), (21, 13), (16, 15)], "z")
    p.ell(11, 7, 16, 14, "P")
    p.rect(12, 9, 13, 10, "E")
    p.rect(18, 9, 19, 10, "E")
    p.line([(12, 12), (15, 13)], "B")
    p.line([(17, 13), (20, 12)], "j")
    # кивер с плюмажем
    p.rect(11, 1, 21, 6, "E")
    p.rect(16, 1, 21, 6, "j")
    p.line([(11, 5), (21, 5)], "m")
    p.ell(14, -3, 19, 2, "h")
    p.outline()
    return p


def osevoy():
    p = Pix()
    # оси через всю фигуру: штрих-пунктир, как на чертеже
    for x in range(0, S, 4):
        p.line([(x, 16), (x + 2, 16)], "J")
    for y in range(0, S, 4):
        p.line([(16, y), (16, y + 2)], "J")
    # туловище из засечек
    p.poly([(9, 31), (11, 20), (21, 20), (23, 31)], "D")
    for y in range(22, 31, 3):
        p.line([(11, y), (21, y)], "J")
    p.line([(16, 20), (16, 31)], "I")
    # лицо — координатная сетка
    p.rect(7, 3, 25, 19, "D")
    for x in range(7, 26, 3):
        p.line([(x, 3), (x, 19)], "J")
    for y in range(3, 20, 3):
        p.line([(7, y), (25, y)], "J")
    p.line([(7, 3), (25, 3), (25, 19), (7, 19), (7, 3)], "I")
    p.rect(12, 9, 13, 10, "I")
    p.rect(19, 9, 20, 10, "I")
    p.line([(13, 15), (19, 15)], "I")
    # кружки осей «А» и «1»
    p.ell(0, 0, 6, 6, "D")
    p.line([(3, 2), (2, 5)], "I")
    p.line([(3, 2), (4, 5)], "I")
    p.px(3, 4, "I")
    p.ell(26, 24, 31, 30, "D")
    p.line([(28, 25), (28, 29)], "Ω")
    p.px(27, 26, "Ω")
    # рука с маркером
    p.line([(21, 22), (27, 20)], "I")
    p.rect(27, 18, 29, 21, "Ω")
    p.outline()
    for cx, cy, r in ((3, 3, 3), (28, 27, 3)):
        p.line([(cx - r, cy), (cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], "I")
    return p


HEROES = {"kalyanych": kalyanych, "lisivy": lisivy, "ugolek": ugolek, "fomich": fomich,
          "gavrilych": gavrilych, "tomik": tomik, "plumbiy": plumbiy, "osevoy": osevoy}

# цвета «зеркал» комнат на орбите: тёмный, средний, яркий
ORBS = {
    "shelf": ("#2a0f22", "#7a1f4a", "#ff5fa8"),
    "garden": ("#0b2410", "#2f7a2a", "#b6ff5a"),
    "hookah": ("#2a0f06", "#a8471a", "#ffb05a"),
    "ai": ("#071a2a", "#1f6aa8", "#6ff0ff"),
    "games": ("#1a1030", "#5a3aa8", "#c89bff"),
    "minis": ("#1a1a1a", "#7a7f8f", "#ffe66a"),
    "anime": ("#200a2a", "#8a2a9e", "#ff7ae0"),
    "thoughts": ("#2a1206", "#c4551f", "#ffd259"),
    "search": ("#141a06", "#6d7a1a", "#e6ff3a"),
}


def hexrgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def orb(key, n=56, seed=0):
    """Круглое «зеркало» с глитчевой пиксельной рябью, как планеты на espy.world."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    r = np.hypot(xx - c, yy - c) / c
    field = np.zeros((n, n), np.float32)
    for _ in range(5):
        fx, fy = rng.uniform(.08, .32, 2)
        ph = rng.uniform(0, math.tau)
        field += np.sin(xx * fx + np.sin(yy * fy * 1.7 + ph) * 2.2 + ph)
    field += rng.uniform(-.6, .6, (n, n))
    # полосы помех
    for y in rng.integers(0, n, 4):
        field[y:y + rng.integers(1, 3), :] += rng.uniform(-1.5, 1.5)
    field = (field - field.min()) / (np.ptp(field) + 1e-6)
    shade = np.clip(field * 1.15 - r ** 3 * .55 + (1 - np.hypot(xx - c * .7, yy - c * .6) / c) * .25, 0, 1)
    dark, mid, hi = (hexrgb(h) for h in ORBS[key])
    q = np.floor(shade * 5).clip(0, 4)
    col = np.where(q[..., None] < 2, dark + (mid - dark) * (q[..., None] / 2),
                   mid + (hi - mid) * ((q[..., None] - 2) / 2))
    alpha = (r <= 1).astype(np.uint8) * 255
    img = np.dstack([col.clip(0, 255).astype(np.uint8), alpha])
    return Image.fromarray(img, "RGBA")


def moss(w=128, h=256, seed=5):
    """Грибница Сумеречного леса: извилистые жилы, бесшовно по обеим осям (шум, сглаженный через FFT)."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(size=(h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f = np.real(np.fft.ifft2(np.fft.fft2(noise) * np.exp(-(fx ** 2 + fy ** 2) / (2 * .035 ** 2))))
    f = (f - f.min()) / np.ptp(f)
    band = np.abs(((f * 7) % 1) - .5)
    img = np.zeros((h, w, 4), np.uint8)
    img[..., :3] = (8, 6, 12)
    img[..., 3] = 255
    img[band < .17] = (58, 14, 74, 255)
    img[band < .11] = (150, 30, 120, 255)
    img[band < .05] = (228, 62, 160, 255)
    img[(band < .05) & (f > .62)] = (255, 106, 31, 255)
    return Image.fromarray(img, "RGBA")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in HEROES.items():
        fn().image().save(OUT / f"{name}.png", optimize=True)
    for i, key in enumerate(ORBS):
        orb(key, seed=i * 7 + 3).save(OUT / f"orb-{key}.png", optimize=True)
    moss().save(OUT / "moss.png", optimize=True)
    print("герои нарисованы:", OUT)


if __name__ == "__main__":
    main()
