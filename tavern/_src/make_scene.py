#!/usr/bin/env python3
"""Рисует общий зал трактира (scene.svg). Запускать, только если хотите перерисовать сцену.

Плейсхолдеры {{count:ai}} и т.п. подставляет build.py.
"""
import math
import random
from pathlib import Path

random.seed(7)
INK = "#1a100a"
OUT = Path(__file__).resolve().parent / "scene.svg"


def books(x0, x1, shelf_y, tallest=84):
    colors = ["#9b2226", "#2f4a6b", "#6b7a3a", "#b8860b", "#5a2a5a", "#3e5c6b", "#8b4513", "#e8dcc0", "#264d3b"]
    out, x = [], x0
    while x < x1 - 10:
        w = random.randint(11, 20)
        if x + w > x1:
            break
        h = random.randint(tallest - 28, tallest)
        c = random.choice(colors)
        if random.random() < 0.12 and x + h < x1:  # книга лежит
            out.append(f'<rect x="{x}" y="{shelf_y - w}" width="{h - 20}" height="{w}" fill="{c}" stroke="{INK}" stroke-width="2.5"/>')
            x += h - 18
            continue
        out.append(f'<rect x="{x}" y="{shelf_y - h}" width="{w}" height="{h}" fill="{c}" stroke="{INK}" stroke-width="2.5"/>')
        band = "#e8c66a" if c != "#b8860b" else "#6b3d12"
        out.append(f'<path d="M{x + 2} {shelf_y - h + 10}h{w - 4}M{x + 2} {shelf_y - 12}h{w - 4}" stroke="{band}" stroke-width="2"/>')
        x += w + random.choice([0, 1, 2])
    return "\n".join(out)


def gear(cx, cy, r, teeth, cls):
    pts = []
    for i in range(teeth * 2):
        a = math.pi * 2 * i / (teeth * 2)
        rr = r if i % 2 == 0 else r * 0.8
        a2 = a + math.pi / (teeth * 2)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        pts.append((cx + rr * math.cos(a2), cy + rr * math.sin(a2)))
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
    return (f'<g class="{cls}" style="transform-origin:{cx}px {cy}px"><path d="{d}" fill="#b08d57" stroke="{INK}" stroke-width="2.5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.35:.1f}" fill="#6b4a2a" stroke="{INK}" stroke-width="2.5"/></g>')


def soldier(x, base_y, color, flag=False, spear=True):
    s = [f'<ellipse cx="{x}" cy="{base_y}" rx="9" ry="3" fill="#2a1c14"/>',
         f'<path d="M{x - 6} {base_y - 1}l1-18h10l1 18z" fill="{color}" stroke="{INK}" stroke-width="2"/>',
         f'<circle cx="{x}" cy="{base_y - 23}" r="5" fill="#e8c9a0" stroke="{INK}" stroke-width="2"/>',
         f'<path d="M{x - 6} {base_y - 25}q6-9 12 0z" fill="#8a8a8a" stroke="{INK}" stroke-width="1.5"/>']
    if spear:
        s.append(f'<path d="M{x + 8} {base_y}V{base_y - 42}" stroke="#5a3a22" stroke-width="2"/>')
        if flag:
            s.append(f'<path d="M{x + 8} {base_y - 42}h14l-4 5 4 5h-14z" fill="{color}" stroke="{INK}" stroke-width="1.5"/>')
        else:
            s.append(f'<path d="M{x + 5} {base_y - 42}l3-7 3 7z" fill="#cfcfcf" stroke="{INK}" stroke-width="1.2"/>')
    return "".join(s)


def label(cx, cy, text, w=None):
    w = w or max(150, int(len(text) * 11.5) + 40)
    x = cx - w / 2
    return f"""<g class="lbl" transform="translate({x:.0f} {cy - 22})">
  <path d="M8 4h{w - 16}l-6 15 6 15H8l6-15z" fill="#f1e2c0" stroke="{INK}" stroke-width="2.5"/>
  <path d="M8 4l-8 6 6 9-6 9 8 6M{w - 8} 4l8 6-6 9 6 9-8 6" fill="#c9b27f" stroke="{INK}" stroke-width="2.5"/>
  <text x="{w / 2:.0f}" y="25" text-anchor="middle">{text}</text>
</g>"""


def flame(x, y, s=1.0, cls="flame"):
    return (f'<path class="{cls}" style="transform-origin:{x}px {y}px" d="M{x} {y}q{-6 * s} {-10 * s} 0 {-22 * s}q{6 * s} {12 * s} 0 {22 * s}z" fill="#ffcf4a" stroke="#e25822" stroke-width="1.5"/>')


def candle(x, y, h=26):
    return (f'<rect x="{x - 5}" y="{y - h}" width="10" height="{h}" fill="#f3ead2" stroke="{INK}" stroke-width="2"/>'
            f'<circle cx="{x}" cy="{y - h - 10}" r="16" fill="url(#candleGlow)"/>' + flame(x, y - h - 1, 0.8, "flame fl2"))


stars = "".join(f'<circle class="twinkle" style="animation-delay:{random.random() * 4:.1f}s" cx="{random.randint(82, 198)}" cy="{random.randint(150, 330)}" r="{random.choice([1.2, 1.6, 2])}" fill="#fff6c8"/>' for _ in range(18))

army = []
colors = ["#6b7a3a", "#8b1e1e", "#3e5c6b", "#3f6b2a"]
for shelf_i, sy in enumerate([298, 398, 498]):
    for j in range(5):
        c = colors[(shelf_i + j) % 4] if shelf_i else colors[j % 4]
        army.append(soldier(952 + j * 38, sy - 2, c, flag=(j % 2 == 0), spear=True))

svg = f"""<svg class="scene" viewBox="0 0 1200 700" role="img" aria-labelledby="scene-title" xmlns="http://www.w3.org/2000/svg">
<title id="scene-title">Общий зал трактира: окно с огородом, книжная полка, очаг, кальян, стол алхимика с магическим шаром, шкаф с оловянными воинами</title>
<defs>
  <pattern id="stones" width="120" height="60" patternUnits="userSpaceOnUse">
    <rect width="120" height="60" fill="#3a2a1f"/>
    <path d="M2 2h54v26H2zM60 2h58v26H60zM-28 32h56v26h-56zM32 32h56v26H32zM92 32h56v26H92z" fill="#4a3627" stroke="#24170f" stroke-width="3"/>
    <path d="M10 10l8 2M70 18l10-3M40 44l12 2M100 40l6 6" stroke="#5b4432" stroke-width="2"/>
  </pattern>
  <pattern id="planks" width="200" height="36" patternUnits="userSpaceOnUse">
    <rect width="200" height="36" fill="#5a3a22"/>
    <path d="M0 35h200M70 0v36M160 0v18M20 18v18" stroke="#2e1d11" stroke-width="3"/>
    <path d="M10 10q20-4 40 0M100 24q20 4 40 0" stroke="#6e4a2e" stroke-width="2" fill="none"/>
  </pattern>
  <linearGradient id="night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1330"/><stop offset="1" stop-color="#2b3a6b"/></linearGradient>
  <radialGradient id="hearthGlow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffb347" stop-opacity=".55"/><stop offset=".6" stop-color="#ff7b00" stop-opacity=".12"/><stop offset="1" stop-color="#ff7b00" stop-opacity="0"/></radialGradient>
  <radialGradient id="candleGlow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#ffd27a" stop-opacity=".7"/><stop offset="1" stop-color="#ffd27a" stop-opacity="0"/></radialGradient>
  <radialGradient id="orb" cx="0.38" cy="0.35" r="0.7"><stop offset="0" stop-color="#e6fbff"/><stop offset=".45" stop-color="#6fd6e8"/><stop offset="1" stop-color="#1f5f7a"/></radialGradient>
  <radialGradient id="orbGlow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#7fe7ff" stop-opacity=".6"/><stop offset="1" stop-color="#7fe7ff" stop-opacity="0"/></radialGradient>
  <radialGradient id="vignette" cx="0.5" cy="0.55" r="0.75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".65"/></radialGradient>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3"/><feColorMatrix values="0 0 0 0 .1  0 0 0 0 .06  0 0 0 0 .03  0 0 0 .5 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
</defs>

<!-- стены, потолок, пол -->
<rect width="1200" height="560" fill="url(#stones)"/>
<rect x="0" y="0" width="1200" height="50" fill="#3a2415" stroke="{INK}" stroke-width="3"/>
<path d="M0 50h1200" stroke="{INK}" stroke-width="4"/>
<path d="M120 0v50M360 0v50M600 0v50M840 0v50M1080 0v50" stroke="#24170f" stroke-width="4"/>
<rect x="0" y="560" width="1200" height="140" fill="url(#planks)"/>
<rect x="0" y="552" width="1200" height="12" fill="#2e1d11" stroke="{INK}" stroke-width="3"/>
<rect x="0" y="50" width="26" height="510" fill="#4a2e1a" stroke="{INK}" stroke-width="3"/>
<rect x="1174" y="50" width="26" height="510" fill="#4a2e1a" stroke="{INK}" stroke-width="3"/>
<circle class="hearth-glow" cx="580" cy="470" r="420" fill="url(#hearthGlow)"/>

<!-- люстра -->
<g class="chandelier" style="transform-origin:600px 0px">
  <path d="M600 50v48" stroke="{INK}" stroke-width="3"/>
  <ellipse cx="600" cy="112" rx="90" ry="14" fill="none" stroke="#3a2415" stroke-width="7"/>
  <ellipse cx="600" cy="112" rx="90" ry="14" fill="none" stroke="{INK}" stroke-width="2"/>
  <path d="M600 98L520 110M600 98L680 110M600 98L600 126" stroke="{INK}" stroke-width="2"/>
  {candle(520, 112, 20)}{candle(560, 124, 20)}{candle(640, 124, 20)}{candle(680, 112, 20)}
</g>

<!-- ОГОРОД: окно и горшки -->
<a class="hot" href="garden.html" aria-label="Огород трактирщика: растения, {{{{count:garden}}}} свитков">
 <g class="obj">
  <path d="M52 370V172Q140 76 228 172V370Z" fill="#5a3a22" stroke="{INK}" stroke-width="3"/>
  <path d="M70 356V178Q140 104 210 178V356Z" fill="url(#night)" stroke="{INK}" stroke-width="3"/>
  {stars}
  <circle cx="176" cy="168" r="17" fill="#f3e6b3"/><circle cx="184" cy="162" r="15" fill="#15204a" opacity=".9"/>
  <path d="M140 110V356M70 256h140" stroke="#5a3a22" stroke-width="7"/><path d="M140 110V356M70 256h140" stroke="{INK}" stroke-width="2"/>
  <rect x="40" y="356" width="200" height="18" fill="#6e4a2e" stroke="{INK}" stroke-width="3"/>
  <!-- кактус -->
  <path d="M66 356l4-26h26l4 26z" fill="#b5542c" stroke="{INK}" stroke-width="2.5"/>
  <path d="M76 330v-38q7-10 14 0v38z" fill="#4c8a3c" stroke="{INK}" stroke-width="2.5"/>
  <path d="M76 312h-6v-14q3-5 6 0M90 318h6v-16q-3-5-6 0" fill="#4c8a3c" stroke="{INK}" stroke-width="2.5"/>
  <circle cx="83" cy="290" r="4" fill="#e85d9b" stroke="{INK}" stroke-width="1.5"/>
  <!-- монстера -->
  <path d="M112 356l5-30h36l5 30z" fill="#8b4513" stroke="{INK}" stroke-width="2.5"/>
  <g class="sway" style="transform-origin:135px 326px">
   <path d="M135 326q-4-40-30-62M135 326q6-44 34-66M135 326q0-30 0-56" stroke="#2f5a2f" stroke-width="3" fill="none"/>
   <path d="M105 264q-26-2-24 20 18 6 24-20zM169 260q24-6 28 16-18 10-28-16zM135 270q-18-16 0-34 18 16 0 34z" fill="#3f7a35" stroke="{INK}" stroke-width="2.5"/>
   <path d="M92 272l8 4M180 268l8-2M135 250v10" stroke="#8fc07c" stroke-width="2"/>
  </g>
  <!-- чили -->
  <path d="M176 356l4-22h30l4 22z" fill="#b5542c" stroke="{INK}" stroke-width="2.5"/>
  <path d="M195 334v-40M195 314l-14-12M195 304l14-12" stroke="#2f5a2f" stroke-width="3"/>
  <ellipse cx="180" cy="298" rx="8" ry="5" fill="#4c8a3c" stroke="{INK}" stroke-width="2"/><ellipse cx="210" cy="290" rx="8" ry="5" fill="#4c8a3c" stroke="{INK}" stroke-width="2"/>
  <path d="M186 312q-2 12 4 16q2-10-4-16zM203 300q4 12 0 18q-4-8 0-18z" fill="#e0301e" stroke="{INK}" stroke-width="1.5"/>
 </g>
 {label(140, 70, "Огород ✠ {{count:garden}}")}
</a>

<!-- ПОЛКА -->
<a class="hot" href="shelf.html" aria-label="Книжная полка: книги, манга, аниме, {{{{count:shelf}}}} свитков">
 <g class="obj">
  <rect x="252" y="130" width="186" height="422" fill="#4a2e1a" stroke="{INK}" stroke-width="3"/>
  <rect x="264" y="142" width="162" height="398" fill="#24170f"/>
  {books(268, 424, 232)}
  {books(268, 424, 332)}
  {books(268, 424, 432)}
  {books(268, 424, 530, 78)}
  <rect x="258" y="232" width="174" height="10" fill="#6e4a2e" stroke="{INK}" stroke-width="2.5"/>
  <rect x="258" y="332" width="174" height="10" fill="#6e4a2e" stroke="{INK}" stroke-width="2.5"/>
  <rect x="258" y="432" width="174" height="10" fill="#6e4a2e" stroke="{INK}" stroke-width="2.5"/>
  <rect x="244" y="120" width="202" height="14" fill="#6e4a2e" stroke="{INK}" stroke-width="3"/>
  <!-- череп и свеча наверху -->
  <path d="M300 120q0-24 20-24t20 24z" fill="#efe4c8" stroke="{INK}" stroke-width="2.5"/>
  <circle cx="313" cy="108" r="4" fill="{INK}"/><circle cx="327" cy="108" r="4" fill="{INK}"/><path d="M316 118v-4M320 118v-4M324 118v-4" stroke="{INK}" stroke-width="1.5"/>
  {candle(400, 120, 22)}
 </g>
 {label(345, 76, "Полка ✠ {{count:shelf}}")}
</a>

<!-- ОЧАГ = летопись / поиск -->
<a class="hot" href="search.html" aria-label="Очаг писаря: поиск по всем {{{{count:all}}}} свиткам">
 <g class="obj">
  <path d="M462 552V250h236v302z" fill="#6a5a4c" stroke="{INK}" stroke-width="3"/>
  <path d="M462 290h236M462 340h236M462 390h236M462 440h236M462 490h236M520 250v40M600 250v40M650 290v50M500 340v50M560 390v50M680 390v50M520 490v62M640 490v62" stroke="#3d322a" stroke-width="3"/>
  <path d="M492 552V396Q580 310 668 396V552Z" fill="#120804" stroke="{INK}" stroke-width="3"/>
  <circle class="hearth-glow" cx="580" cy="500" r="90" fill="url(#hearthGlow)"/>
  <path d="M520 540l120-16M530 522l110 24" stroke="#4a2e1a" stroke-width="12" stroke-linecap="round"/>
  <path d="M520 540l120-16M530 522l110 24" stroke="{INK}" stroke-width="2" fill="none"/>
  <g class="fire">
   <path class="flame f1" style="transform-origin:580px 530px" d="M540 530q-10-50 20-80q-4 30 16 40q0-40 26-64q-6 40 18 60q16-16 10-36q24 30 6 80z" fill="#ff7b00" stroke="#b83a00" stroke-width="2"/>
   <path class="flame f2" style="transform-origin:580px 530px" d="M556 530q-6-34 14-52q0 24 12 30q4-26 18-38q-2 30 10 40q6-6 6-18q12 20 0 38z" fill="#ffcf4a"/>
   <path class="flame f3" style="transform-origin:580px 530px" d="M570 530q-2-18 8-28q2 14 10 16q2-12 8-18q4 16 0 30z" fill="#fff3b0"/>
  </g>
  <!-- котёл -->
  <path d="M580 330v52" stroke="{INK}" stroke-width="3" stroke-dasharray="6 3"/>
  <path d="M548 392q0 36 32 36t32-36z" fill="#2a2a2a" stroke="{INK}" stroke-width="3"/>
  <ellipse cx="580" cy="392" rx="34" ry="8" fill="#3c7a3c" stroke="{INK}" stroke-width="3"/>
  <circle class="bubble" cx="572" cy="388" r="3" fill="#6fbf5f"/><circle class="bubble b2" cx="590" cy="390" r="2.5" fill="#6fbf5f"/>
  <rect x="440" y="232" width="280" height="24" fill="#6e4a2e" stroke="{INK}" stroke-width="3"/>
  <!-- на полке над очагом: песочные часы, кружка -->
  <path d="M480 232v-30h22v30zM484 206l14 10-14 10" fill="none" stroke="{INK}" stroke-width="2.5"/>
  <path d="M484 206h14l-7 10zM484 228h14l-7-8z" fill="#e8c66a" stroke="{INK}" stroke-width="1.5"/>
  <path d="M660 232v-26h24v26zM684 212q10 0 10 8t-10 8" fill="#8a8a8a" stroke="{INK}" stroke-width="2.5"/>
  <path d="M660 208q12-8 24 0" fill="#f3ead2" stroke="{INK}" stroke-width="2"/>
  <!-- щит с гербом -->
  <path d="M552 140h56v36q0 24-28 36q-28-12-28-36z" fill="#9b2226" stroke="{INK}" stroke-width="3"/>
  <path d="M580 150v54M558 172h44" stroke="#e8c66a" stroke-width="5"/>
  <path d="M562 150q18 10 36 0" stroke="{INK}" stroke-width="1.5" fill="none"/>
 </g>
 {label(580, 290, "Картотека ✠ {{count:all}}", 230)}
</a>

<!-- ДОСКА ОБЪЯВЛЕНИЙ = канал -->
<a class="hot" href="{{{{channel_url}}}}" aria-label="Доска у входа: канал в Telegram">
 <g class="obj">
  <rect x="748" y="72" width="150" height="104" fill="#8a5a2b" stroke="{INK}" stroke-width="3"/>
  <rect x="758" y="82" width="130" height="84" fill="#b0834f" stroke="{INK}" stroke-width="2"/>
  <path d="M766 90h50v44h-50z" fill="#f1e2c0" stroke="{INK}" stroke-width="2" transform="rotate(-4 790 110)"/>
  <path d="M772 100h36M772 108h30M772 116h34M772 124h20" stroke="#7a6a5a" stroke-width="2" transform="rotate(-4 790 110)"/>
  <path d="M826 92h54v38h-54z" fill="#f1e2c0" stroke="{INK}" stroke-width="2" transform="rotate(5 850 110)"/>
  <text x="853" y="116" font-size="13" text-anchor="middle" transform="rotate(5 850 110)" class="svg-mono">t.me</text>
  <path d="M800 138h60v24h-60z" fill="#e8dcc0" stroke="{INK}" stroke-width="2" transform="rotate(-2 830 150)"/>
  <text x="830" y="155" font-size="11" text-anchor="middle" class="svg-mono" transform="rotate(-2 830 150)">РАЗЫСК.</text>
  <circle cx="790" cy="90" r="3.5" fill="#9b2226"/><circle cx="852" cy="94" r="3.5" fill="#9b2226"/><circle cx="830" cy="140" r="3.5" fill="#9b2226"/>
 </g>
 {label(823, 206, "Канал ↗", 150)}
</a>

<!-- КЕЛЬЯ ИИ: стол алхимика -->
<a class="hot" href="ai.html" aria-label="Келья механических духов: ИИ-агенты, {{{{count:ai}}}} свитков">
 <g class="obj">
  {gear(760, 262, 26, 10, "gear g1")}{gear(800, 296, 17, 8, "gear g2")}{gear(746, 312, 13, 7, "gear g1")}
  <!-- магическое зеркало -->
  <rect x="826" y="300" width="84" height="104" rx="6" fill="#b8860b" stroke="{INK}" stroke-width="3"/>
  <path d="M840 300q28-26 56 0" fill="#b8860b" stroke="{INK}" stroke-width="3"/>
  <circle cx="868" cy="288" r="5" fill="#9b2226" stroke="{INK}" stroke-width="2"/>
  <rect x="836" y="310" width="64" height="84" fill="#0c1f18" stroke="{INK}" stroke-width="2"/>
  <g class="code">
   <path d="M842 322h30M846 332h40M846 342h24M842 352h36M846 362h18M842 372h28" stroke="#58e08a" stroke-width="3"/>
   <rect class="cursor" x="874" y="368" width="7" height="8" fill="#58e08a"/>
  </g>
  <!-- стол -->
  <rect x="728" y="430" width="196" height="18" fill="#6e4a2e" stroke="{INK}" stroke-width="3"/>
  <path d="M742 448v104M910 448v104" stroke="#4a2e1a" stroke-width="12"/><path d="M742 448v104M910 448v104" stroke="{INK}" stroke-width="2"/>
  <rect x="826" y="404" width="84" height="26" fill="#6e4a2e" stroke="{INK}" stroke-width="2.5"/>
  <!-- магический шар -->
  <circle class="orb-glow" cx="782" cy="392" r="66" fill="url(#orbGlow)"/>
  <path d="M760 430l6-16h32l6 16z" fill="#6b4a2a" stroke="{INK}" stroke-width="2.5"/>
  <circle cx="782" cy="388" r="30" fill="url(#orb)" stroke="{INK}" stroke-width="3"/>
  <g class="orb-eye"><ellipse cx="782" cy="390" rx="11" ry="7" fill="#fff" stroke="{INK}" stroke-width="2"/><circle cx="782" cy="390" r="4" fill="{INK}"/></g>
  <path d="M766 374q6-8 14-8" stroke="#fff" stroke-width="3" fill="none" opacity=".8"/>
  <!-- свитки и перо -->
  <path d="M736 430q0-12 12-12h14q-10 4-10 12z" fill="#f1e2c0" stroke="{INK}" stroke-width="2"/>
  {candle(912, 430, 18)}
 </g>
 {label(820, 480, "Келья ИИ ✠ {{count:ai}}", 210)}
</a>

<!-- ОРУЖЕЙНАЯ: шкаф с воинами -->
<a class="hot" href="minis.html" aria-label="Оружейная палата: миниатюры, {{{{count:minis}}}} свитков">
 <g class="obj">
  <rect x="934" y="200" width="214" height="352" fill="#4a2e1a" stroke="{INK}" stroke-width="3"/>
  <path d="M922 200h238l-14-22H936z" fill="#6e4a2e" stroke="{INK}" stroke-width="3"/>
  <rect x="946" y="212" width="190" height="328" fill="#1f1510"/>
  {''.join(army)}
  <rect x="940" y="298" width="202" height="8" fill="#6e4a2e" stroke="{INK}" stroke-width="2"/>
  <rect x="940" y="398" width="202" height="8" fill="#6e4a2e" stroke="{INK}" stroke-width="2"/>
  <rect x="940" y="498" width="202" height="8" fill="#6e4a2e" stroke="{INK}" stroke-width="2"/>
  <rect x="946" y="212" width="190" height="328" fill="#bfe3ff" opacity=".08"/>
  <path d="M960 222l40 60M1080 222l30 44" stroke="#fff" stroke-width="3" opacity=".25"/>
  <path d="M1041 212v328" stroke="{INK}" stroke-width="3"/>
  <circle cx="1034" cy="380" r="3" fill="#e8c66a" stroke="{INK}"/><circle cx="1048" cy="380" r="3" fill="#e8c66a" stroke="{INK}"/>
  <!-- шлем на шкафу -->
  <path d="M1010 178q0-34 32-34t32 34z" fill="#9a9a9a" stroke="{INK}" stroke-width="3"/>
  <path d="M1042 144v34M1020 162h44" stroke="{INK}" stroke-width="2.5"/>
  <path d="M1042 144q10-16 24-12q-8 6-6 14" fill="#9b2226" stroke="{INK}" stroke-width="2"/>
 </g>
 {label(1041, 120, "Оружейная ✠ {{count:minis}}", 230)}
</a>

<!-- ДЫМНАЯ ГОРНИЦА: стол с кальяном (передний план) -->
<a class="hot" href="hookah.html" aria-label="Дымная горница: кальян и забивки, {{{{count:hookah}}}} свитков">
 <g class="obj">
  <path d="M316 610l-26 76h24l14-60zM376 610l26 76h-24l-14-60z" fill="#4a2e1a" stroke="{INK}" stroke-width="3"/>
  <ellipse cx="346" cy="604" rx="124" ry="26" fill="#7a5232" stroke="{INK}" stroke-width="3"/>
  <ellipse cx="346" cy="600" rx="112" ry="20" fill="#8a5f3a"/>
  <!-- колба -->
  <path d="M330 600q-34-6-34-38q0-22 22-36h56q22 14 22 36q0 32-34 38z" fill="#3b6ea5" stroke="{INK}" stroke-width="3" opacity=".95"/>
  <path d="M302 566q44 10 84 0" stroke="#8fc3ff" stroke-width="3" fill="none" opacity=".6"/>
  <circle class="bubble" cx="336" cy="580" r="4" fill="#a8d4ff"/><circle class="bubble b2" cx="352" cy="584" r="3" fill="#a8d4ff"/>
  <!-- шахта -->
  <rect x="338" y="436" width="16" height="92" fill="#b8860b" stroke="{INK}" stroke-width="3"/>
  <path d="M330 470h32M330 500h32" stroke="{INK}" stroke-width="3"/>
  <ellipse cx="346" cy="468" rx="20" ry="6" fill="#d9a441" stroke="{INK}" stroke-width="2.5"/>
  <!-- чаша и калауд -->
  <path d="M326 436h40l-6-22h-28z" fill="#a0522d" stroke="{INK}" stroke-width="3"/>
  <path d="M322 414h48l-4-12h-40z" fill="#8a8a8a" stroke="{INK}" stroke-width="2.5"/>
  <rect x="332" y="398" width="8" height="5" fill="#ff7b00"/><rect x="344" y="398" width="8" height="5" fill="#ff7b00"/><rect x="356" y="398" width="8" height="5" fill="#ff7b00"/>
  <!-- шланг -->
  <path d="M362 494q60 6 70 50q6 30 34 40" stroke="#2f4a2f" stroke-width="8" fill="none" stroke-linecap="round"/>
  <path d="M362 494q60 6 70 50q6 30 34 40" stroke="{INK}" stroke-width="2" fill="none" stroke-dasharray="3 6"/>
  <rect x="460" y="578" width="24" height="9" rx="3" fill="#b8860b" stroke="{INK}" stroke-width="2" transform="rotate(20 472 582)"/>
  <!-- кружка -->
  <path d="M232 598v-30h26v30zM258 574q12 0 12 10t-12 10" fill="#8a8a8a" stroke="{INK}" stroke-width="2.5"/>
  <path d="M230 572q14-10 30 0" fill="#f3ead2" stroke="{INK}" stroke-width="2"/>
  <!-- дым -->
  <g class="smoke">
   <circle class="puff p1" cx="348" cy="386" r="10" fill="#d9d2c8"/>
   <circle class="puff p2" cx="340" cy="380" r="8" fill="#d9d2c8"/>
   <circle class="puff p3" cx="356" cy="384" r="9" fill="#d9d2c8"/>
  </g>
 </g>
 {label(346, 356, "Дымная горница ✠ {{count:hookah}}", 280)}
</a>

<!-- кот у очага -->
<g class="cat" aria-hidden="true">
  <path d="M620 600q0-26 34-26q30 0 36 22q2 10-6 12h-60q-6 0-4-8z" fill="#2b2b2b" stroke="{INK}" stroke-width="2.5"/>
  <path d="M676 580l6-14 6 12zM690 584l8-10 2 14z" fill="#2b2b2b" stroke="{INK}" stroke-width="2"/>
  <path d="M618 606q-26 6-20-12" stroke="#2b2b2b" stroke-width="8" fill="none" stroke-linecap="round"/>
  <path d="M680 594q4 3 8 0" stroke="#e8c66a" stroke-width="2" fill="none"/>
  <text class="zzz" x="700" y="566" font-size="16">z</text><text class="zzz z2" x="712" y="552" font-size="12">z</text>
</g>

<!-- бочка -->
<g aria-hidden="true">
  <path d="M1040 690q-14-54 0-110h90q14 56 0 110z" fill="#7a4a26" stroke="{INK}" stroke-width="3"/>
  <path d="M1034 606h102M1034 664h102" stroke="#3a3a3a" stroke-width="7"/><path d="M1034 606h102M1034 664h102" stroke="{INK}" stroke-width="1.5"/>
  <path d="M1085 580v110" stroke="#5a3a22" stroke-width="2"/>
  <path d="M1066 580v-26h26v26zM1092 560q12 0 12 10t-12 10" fill="#8a8a8a" stroke="{INK}" stroke-width="2.5"/>
  <path d="M1064 556q14-10 30 0" fill="#f3ead2" stroke="{INK}" stroke-width="2"/>
</g>

<!-- маргиналия: улитка против рыцаря -->
<g class="snail-duel" aria-hidden="true">
  <g class="knight">
   <path d="M800 686l6-40h26l6 40z" fill="#9a9a9a" stroke="{INK}" stroke-width="2.5"/>
   <circle cx="819" cy="636" r="12" fill="#b0b0b0" stroke="{INK}" stroke-width="2.5"/>
   <path d="M810 636h18" stroke="{INK}" stroke-width="2.5"/>
   <path d="M813 642q6-3 12 0" stroke="{INK}" stroke-width="1.5" fill="none" transform="rotate(180 819 642)"/>
   <path d="M806 656l-24 10" stroke="#b0b0b0" stroke-width="5" stroke-linecap="round"/>
   <path d="M780 668l-20 0" stroke="#dcdcdc" stroke-width="3"/>
   <path d="M834 656q12 4 6 16" stroke="#b0b0b0" stroke-width="5" fill="none" stroke-linecap="round"/>
  </g>
  <g class="snail">
   <path d="M690 688q-4-12 12-12h48q10 0 8 12z" fill="#c9b27f" stroke="{INK}" stroke-width="2.5"/>
   <circle cx="722" cy="664" r="20" fill="#b5542c" stroke="{INK}" stroke-width="2.5"/>
   <path d="M722 664m-12 0a12 12 0 1 1 12 12a6 6 0 1 1 -6 -6" fill="none" stroke="{INK}" stroke-width="2"/>
   <path d="M752 678l6-20M756 678l12-16" stroke="{INK}" stroke-width="2"/><circle cx="758" cy="657" r="2.5" fill="{INK}"/><circle cx="768" cy="661" r="2.5" fill="{INK}"/>
   <path d="M740 672l40-10" stroke="#5a3a22" stroke-width="3"/><path d="M780 662l8-4-6 8z" fill="#dcdcdc" stroke="{INK}" stroke-width="1.5"/>
  </g>
</g>

<rect width="1200" height="700" fill="url(#vignette)" pointer-events="none"/>
<rect width="1200" height="700" filter="url(#grain)" opacity=".35" pointer-events="none"/>
</svg>
"""
OUT.write_text(svg, encoding="utf-8")
print("scene.svg записан:", OUT)
