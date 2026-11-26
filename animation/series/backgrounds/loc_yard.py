"""Локация «Двор и сад» у семейного дома. Слои для параллакса:
far (небо, холмы, дальний город с минаретом) ×0.4, mid (тихая улица, соседские дома) ×0.7,
main (забор, двор, сад, дом с крыльцом, яблоня, скамейка) ×1.0, fg (трава и цветы у камеры) ×1.25.

Мир 3400×1200. Земля двора: y≈780–1200. Точка посадки подсолнуха — SPOT.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, poly_path, Draw, shade, mix, gradient_rect, radial, ellipse_pts, col
from home_common import LIGHT, lit, box, contact, window, plant_pot, cloud, tree, bush, grain, lamp_glow

WW, WH = 3400, 1200
PARALLAX = dict(far=0.4, mid=0.7, main=1.0, fg=1.25)
SPOT = (1580, 1000)        # где растёт подсолнух (передний край грядки)
DOOR = (2760, 905)         # низ крыльца у двери
GATE = (930, 790)
BENCH = (660, 975)


def _far(P):
    s = skia.Surface(WW, WH); c = s.getCanvas()
    gradient_rect(c, (0, 0, WW, WH), P["sky"])
    if P["sun"]:
        k, sc = P["sun"]
        sx, sy = 600 + 1800 * k, 260 + 260 * k
        radial(c, sx, sy, 640, [(sc, 0.7, 0.0), (sc, 0.22, 0.35), (sc, 0.0, 1.0)])
        c.drawCircle(sx, sy, 58, paint(sc, 0.95, blur=8))
    if P is LIGHT["night"]:
        rng = np.random.default_rng(9)
        for i in range(160):
            c.drawCircle(rng.uniform(0, WW), rng.uniform(0, 560), rng.uniform(0.8, 2.2), paint((255, 255, 240), rng.uniform(0.4, 0.9)))
        c.drawCircle(2500, 200, 44, paint((255, 250, 220), 0.95))
        radial(c, 2500, 200, 220, [((255, 250, 220), 0.25, 0.0), ((255, 250, 220), 0.0, 1.0)])
    rng = np.random.default_rng(2)
    cl = (255, 255, 255) if P["amb"] > 0.85 else mix(P["sky"][1][0], (255, 255, 255), 0.35)
    for i in range(9):
        cloud(c, rng.uniform(0, WW), rng.uniform(80, 330), rng.uniform(40, 85), cl, 0.7)
    haze = P["sky"][-1][0]
    # дальние холмы
    for k, (base, amp, colr) in enumerate(((640, 60, (150, 180, 170)), (680, 40, (130, 170, 140)))):
        pts = [(x, base - amp * (0.5 + 0.5 * math.sin(x / (380 + 120 * k) + k * 2))) for x in range(-40, WW + 80, 40)]
        pts += [(WW + 40, WH), (-40, WH)]
        c.drawPath(smooth_path(pts, tension=0.3), paint(lit(mix(colr, haze, 0.55 - 0.15 * k), P)))
    # дальний городок: крыши и минарет
    town = lit(mix((176, 150, 150), haze, 0.55), P)
    for i in range(26):
        x = rng.uniform(0, WW); w = rng.uniform(50, 110); h = rng.uniform(30, 70)
        c.drawRect(skia.Rect(x, 680 - h, x + w, 720), paint(town))
        c.drawPath(poly_path([(x - 6, 680 - h), (x + w / 2, 680 - h - 26), (x + w + 6, 680 - h)]), paint(shade(town, 0.92)))
    mx = 2050
    c.drawRect(skia.Rect(mx - 7, 520, mx + 7, 700), paint(town))
    c.drawRect(skia.Rect(mx - 11, 570, mx + 11, 577), paint(town))
    c.drawPath(poly_path([(mx - 8, 520), (mx, 490), (mx + 8, 520)]), paint(town))
    dome = smooth_path([(mx + 30, 690), (mx + 40, 640), (mx + 75, 620), (mx + 110, 640), (mx + 120, 690)], tension=0.6)
    c.drawPath(dome, paint(town))
    return s.makeImageSnapshot()


def neighbor_house(c, x, base, w, h, wall, roof, P, seed=1):
    D = Draw(c)
    box(c, x, base - h, x + w, base, wall, P, r=2)
    rp = poly_path([(x - 26, base - h + 4), (x + w / 2, base - h - w * 0.36), (x + w + 26, base - h + 4)])
    D.shape(rp, lit(roof, P), line=lit(shade(roof, 0.6), P), lw=2, shadow=(0, 16, lit(shade(roof, 0.8), P), 6))
    for k in range(3):
        D.stroke([(x - 18 + k * 8, base - h + 2 - k * 10), (x + w + 18 - k * 8, base - h + 2 - k * 10)], lit(shade(roof, 0.8), P), 1.5, alpha=0.4)
    for i in range(2):
        wx = x + w * (0.18 + 0.44 * i)
        c.drawRect(skia.Rect(wx, base - h * 0.72, wx + w * 0.22, base - h * 0.35), paint(lit((150, 190, 214), P)))
        if P["win"] > 0.3:
            c.drawRect(skia.Rect(wx, base - h * 0.72, wx + w * 0.22, base - h * 0.35), paint((255, 214, 140), 0.85 * P["win"]))
        c.drawRect(skia.Rect(wx - 4, base - h * 0.72 - 4, wx + w * 0.22 + 4, base - h * 0.35 + 4), paint(lit((250, 248, 240), P), style="stroke", width=4))
    c.drawRoundRect(skia.Rect(x + w * 0.45, base - h * 0.30, x + w * 0.58, base), 4, 4, paint(lit((150, 100, 74), P)))


def _mid(P):
    s = skia.Surface(WW, WH); c = s.getCanvas(); c.clear(col((0, 0, 0), 0.0))
    D = Draw(c)
    # улица за забором: дорога и тротуар
    gradient_rect(c, (0, 690, WW, 760), [(lit((176, 172, 170), P), 0.0), (lit((160, 156, 156), P), 1.0)])
    c.drawRect(skia.Rect(0, 684, WW, 694), paint(lit((214, 206, 196), P)))
    for x in range(40, WW, 160):
        c.drawRect(skia.Rect(x, 724, x + 70, 728), paint(lit((240, 236, 226), P), 0.7))
    # соседские дома и деревья
    neighbor_house(c, 80, 684, 300, 200, (186, 210, 228), (176, 96, 80), P, 1)
    tree(c, 520, 690, 0.55, P, seed=4, dark=0.92)
    neighbor_house(c, 640, 684, 340, 230, (246, 222, 170), (150, 92, 84), P, 2)
    neighbor_house(c, 1120, 684, 280, 190, (220, 200, 226), (160, 104, 86), P, 3)
    tree(c, 1520, 690, 0.6, P, seed=5, dark=0.92)
    neighbor_house(c, 1640, 684, 320, 210, (210, 226, 196), (170, 100, 80), P, 4)
    # фонарь
    D.stroke([(1500, 690), (1500, 520)], lit((80, 84, 96), P), 5)
    D.stroke([(1500, 525), (1530, 515)], lit((80, 84, 96), P), 4)
    c.drawRoundRect(skia.Rect(1520, 512, 1546, 532), 4, 4, paint(lit((250, 240, 210), P)))
    if P["win"] > 0.3:
        lamp_glow(c, 1533, 522, 90, P, P["win"])
    return s.makeImageSnapshot()


def house(c, P):
    D = Draw(c)
    x0, x1, base, top = 2240, WW + 40, 830, 360
    wallc = (248, 232, 208)
    box(c, x0, top, x1, base, wallc, P, r=2)
    # фактура штукатурки
    rng = np.random.default_rng(6)
    for i in range(140):
        c.drawCircle(rng.uniform(x0, x1), rng.uniform(top, base), rng.uniform(2, 5), paint(lit(shade(wallc, 0.95), P), 0.5))
    # цоколь
    c.drawRect(skia.Rect(x0, base - 60, x1, base), paint(lit((196, 176, 160), P)))
    for xx in range(x0, x1, 70):
        c.drawRect(skia.Rect(xx, base - 60, xx + 66, base - 30), paint(lit((206, 186, 170), P)))
    # крыша
    rp = poly_path([(x0 - 70, top + 10), (x0 + 340, top - 230), (x1 + 60, top - 230), (x1 + 60, top + 10)])
    D.shape(rp, lit((198, 108, 84), P), line=lit((130, 64, 54), P), lw=2.4, shadow=(0, 30, lit((160, 84, 66), P), 8))
    for k in range(7):
        y = top + 4 - k * 33
        xl = x0 - 70 + (k * 33) * (410 / 240)
        D.stroke([(xl, y), (x1 + 60, y)], lit((170, 90, 70), P), 2, alpha=0.6)
    c.drawRect(skia.Rect(x0 - 70, top + 4, x1 + 60, top + 22), paint(lit((240, 236, 226), P)))
    c.drawRect(skia.Rect(x0 - 70, top + 22, x1 + 60, top + 40), paint((60, 40, 40), 0.18, blur=8))
    # окна со шторами и ящиками цветов
    for wx in (2360, 3080):
        window(c, wx, 500, wx + 190, 690, P, view=lambda cc, r: _window_inside(cc, r, P), curtain=(246, 196, 186), sill_plants=False, open_curtains=0.55, seed=int(wx), inside=True)
        box(c, wx - 20, 712, wx + 210, 750, (176, 120, 86), P, r=4)
        bush(c, wx + 95, 716, 0.75, P, flowers=(240, 110, 120), seed=int(wx) % 7)
    # дверь с полукруглым верхом
    dx = DOOR[0]
    door = smooth_path([(dx - 95, 830), (dx - 95, 560), (dx - 60, 505), (dx, 490), (dx + 60, 505), (dx + 95, 560), (dx + 95, 830)], tension=0.4)
    D.shape(door, lit((150, 98, 70), P), line=lit((90, 56, 40), P), lw=3, shadow=(-18, -10, lit((120, 76, 54), P), 8))
    for k in range(3):
        D.stroke([(dx - 70 + 70 * k, 580), (dx - 70 + 70 * k, 810)], lit((120, 76, 54), P), 2, alpha=0.5)
    c.drawCircle(dx + 65, 690, 8, paint(lit((230, 190, 90), P)))
    c.drawOval(skia.Rect(dx - 40, 520, dx + 40, 570), paint(lit((200, 226, 236), P)))
    if P["win"] > 0.3:
        c.drawOval(skia.Rect(dx - 40, 520, dx + 40, 570), paint((255, 214, 140), 0.85 * P["win"]))
    # фонарь у двери
    c.drawRoundRect(skia.Rect(dx + 130, 560, dx + 160, 610), 6, 6, paint(lit((60, 56, 60), P)))
    c.drawRoundRect(skia.Rect(dx + 135, 566, dx + 155, 604), 4, 4, paint((255, 228, 170), 0.6 + 0.4 * P["win"]))
    if P["win"] > 0.3:
        lamp_glow(c, dx + 145, 585, 160, P, P["win"])
    # крыльцо: три ступени
    for k in range(3):
        y = 830 + k * 26
        box(c, dx - 160 - k * 26, y, dx + 160 + k * 26, y + 26, (214, 200, 186), P, r=3)
    # вьющиеся розы у двери
    for side in (-1, 1):
        for i in range(26):
            yy = 500 + i * 13
            xx = dx + side * (115 + 12 * math.sin(i * 0.8))
            c.drawOval(skia.Rect(xx - 12, yy - 7, xx + 12, yy + 7), paint(lit((84, 150, 84), P)))
            if i % 4 == 1:
                c.drawCircle(xx + side * 4, yy, 7, paint(lit((244, 140, 150), P)))


def _window_inside(c, r, P):
    x0, y0, x1, y1 = r
    gradient_rect(c, r, [(lit((250, 226, 196), P, 0.75), 0.0), (lit((226, 196, 170), P, 0.7), 1.0)])
    if P["win"] > 0.3:
        c.drawRect(skia.Rect(*r), paint((255, 206, 140), 0.7 * P["win"]))
    c.drawRect(skia.Rect(x0, y1 - 40, x1, y1), paint(lit((170, 130, 100), P, 0.7)))


def fence(c, x0, x1, base, P, gate=None):
    D = Draw(c)
    wood = (248, 240, 226)
    D.stroke([(x0, base - 90), (x1, base - 90)], lit(shade(wood, 0.8), P), 9)
    D.stroke([(x0, base - 36), (x1, base - 36)], lit(shade(wood, 0.8), P), 9)
    x = x0
    while x < x1:
        if gate and gate[0] - 70 < x < gate[0] + 70:
            x += 34; continue
        pk = poly_path([(x, base), (x, base - 118), (x + 12, base - 132), (x + 24, base - 118), (x + 24, base)])
        D.shape(pk, lit(wood, P), line=lit(shade(wood, 0.6), P), lw=1.8, shadow=(-6, 0, lit(shade(wood, 0.86), P), 3))
        x += 34
    if gate:
        gx = gate[0]
        for side in (-1, 1):
            c.drawRoundRect(skia.Rect(gx + side * 78 - 10, base - 160, gx + side * 78 + 10, base), 3, 3, paint(lit(shade(wood, 0.92), P)))
            c.drawCircle(gx + side * 78, base - 166, 12, paint(lit(shade(wood, 0.92), P)))


def _main(P):
    s = skia.Surface(WW, WH); c = s.getCanvas(); c.clear(col((0, 0, 0), 0.0))
    D = Draw(c)
    # лужайка
    gradient_rect(c, (0, 760, WW, WH), [(lit((150, 196, 120), P), 0.0), (lit((126, 182, 100), P), 0.4), (lit((104, 160, 86), P), 1.0)])
    rng = np.random.default_rng(12)
    for i in range(900):  # травинки
        x, y = rng.uniform(0, WW), 770 + (WH - 770) * rng.random() ** 0.8
        L = 6 + (y - 760) * 0.035
        D.stroke([(x, y), (x + rng.uniform(-3, 3), y - L)], lit((84 + rng.integers(0, 40), 150 + rng.integers(0, 30), 80), P), 1.4, alpha=0.7)
    for i in range(70):  # полевые цветочки
        x, y = rng.uniform(0, WW), rng.uniform(800, 1180)
        cc = [(255, 255, 255), (255, 220, 110), (220, 180, 240)][i % 3]
        c.drawCircle(x, y, 3 + (y - 800) * 0.006, paint(lit(cc, P), 0.9))
    fence(c, -20, 2240, 790, P, gate=GATE)
    house(c, P)
    # тропинка из плитки от калитки к крыльцу
    pts = [(GATE[0], 800), (1060, 890), (1180, 1060), (1600, 1110), (2100, 1090), (2500, 990), (DOOR[0], 935)]
    path_pts = []
    for i in range(46):
        u = i / 45
        k = u * (len(pts) - 1); j = min(int(k), len(pts) - 2); f = k - j
        x = pts[j][0] * (1 - f) + pts[j + 1][0] * f
        y = pts[j][1] * (1 - f) + pts[j + 1][1] * f
        path_pts.append((x, y))
    for i, (x, y) in enumerate(path_pts):
        sc = 0.55 + (y - 790) / 400
        D.ellipse(x + (i % 2) * 18 * sc, y, 34 * sc, 13 * sc, lit((222, 210, 196), P), line=lit((170, 156, 146), P), lw=1.6)
    # грядка с овощами (деревянный бортик)
    bx0, bx1, by0, by1 = 1260, 2000, 900, 990
    c.drawRect(skia.Rect(bx0, by0, bx1, by1), paint(lit((110, 78, 58), P)))
    for k in range(40):
        c.drawCircle(rng.uniform(bx0, bx1), rng.uniform(by0, by1), rng.uniform(3, 7), paint(lit((90, 62, 46), P), 0.8))
    box(c, bx0 - 10, by1 - 6, bx1 + 10, by1 + 18, (176, 126, 86), P, r=3)
    box(c, bx0 - 10, by0 - 10, bx1 + 10, by0 + 4, (160, 114, 78), P, r=3, k=0.9)
    for i, x in enumerate(range(bx0 + 40, bx1 - 20, 70)):
        if abs(x - SPOT[0]) < 90:
            continue
        if i % 3 == 0:  # капуста
            for k in range(6):
                a = k * 1.05
                D.ellipse(x + math.cos(a) * 12, 950 + math.sin(a) * 6, 22, 14, lit((140, 196, 130), P), line=lit((80, 130, 80), P), lw=1.4, rot=a)
            c.drawCircle(x, 948, 14, paint(lit((170, 214, 150), P)))
        elif i % 3 == 1:  # морковь
            for k in range(5):
                D.stroke([(x + (k - 2) * 6, 960), (x + (k - 2) * 12, 900)], lit((90, 160, 80), P), 3)
            c.drawCircle(x, 962, 9, paint(lit((240, 140, 60), P)))
        else:  # клубника
            bush(c, x, 975, 0.45, P, flowers=(255, 255, 255), seed=i)
            for k in range(3):
                c.drawCircle(x - 20 + k * 20, 968, 7, paint(lit((230, 70, 70), P)))
    # кусты и цветы вдоль забора
    for x, fl in ((150, (250, 170, 190)), (1100, (255, 220, 120)), (1700, (220, 170, 240)), (2120, (250, 140, 150))):
        bush(c, x, 800, 0.8, P, flowers=fl, seed=x % 11)
    # яблоня, скамейка, скворечник
    tree(c, 470, 905, 1.25, P, seed=3, apples=12)
    c.drawRect(skia.Rect(395, 470, 445, 520), paint(lit((210, 150, 100), P)))
    c.drawPath(poly_path([(388, 472), (420, 440), (452, 472)]), paint(lit((170, 100, 80), P)))
    c.drawCircle(420, 496, 9, paint((50, 36, 40)))
    contact(c, BENCH[0], BENCH[1] + 4, 300, 0.25)
    box(c, BENCH[0] - 140, BENCH[1] - 70, BENCH[0] + 140, BENCH[1] - 52, (176, 124, 84), P, r=4)
    for lx in (-120, 110):
        c.drawRect(skia.Rect(BENCH[0] + lx, BENCH[1] - 54, BENCH[0] + lx + 14, BENCH[1]), paint(lit((140, 96, 64), P)))
    for lx in (-130, 116):
        c.drawRect(skia.Rect(BENCH[0] + lx, BENCH[1] - 170, BENCH[0] + lx + 12, BENCH[1] - 60), paint(lit((140, 96, 64), P)))
    for k in range(2):
        box(c, BENCH[0] - 145, BENCH[1] - 168 + k * 34, BENCH[0] + 145, BENCH[1] - 146 + k * 34, (186, 132, 90), P, r=3)
    # тень дома и дерева на газоне
    c.drawOval(skia.Rect(2150, 860, WW + 100, 960), paint((40, 50, 40), 0.18, blur=30))
    c.drawOval(skia.Rect(150, 880, 820, 960), paint((40, 50, 40), 0.22, blur=26))
    grain(c, WW, WH, seed=4, strength=5)
    return s.makeImageSnapshot()


def _fg(P):
    s = skia.Surface(WW, WH); c = s.getCanvas(); c.clear(col((0, 0, 0), 0.0))
    D = Draw(c)
    rng = np.random.default_rng(21)
    for cx in list(rng.uniform(0, WW, 10)):
        for i in range(40):
            x = cx + rng.uniform(-90, 90)
            h = rng.uniform(60, 170)
            D.tapered([(x, WH + 10), (x + rng.uniform(-30, 30), WH - h)], 7, 1, lit((70 + rng.integers(0, 40), 130, 70), P, 0.85))
        for i in range(5):
            x, y = cx + rng.uniform(-70, 70), WH - rng.uniform(80, 150)
            for q in range(5):
                b = q * 1.256
                c.drawCircle(x + math.cos(b) * 9, y + math.sin(b) * 9, 8, paint(lit([(255, 255, 255), (250, 200, 90), (240, 160, 190)][i % 3], P, 0.9)))
            c.drawCircle(x, y, 5, paint(lit((255, 220, 110), P)))
    return s.makeImageSnapshot()


def render_layers(preset):
    P = LIGHT[preset]
    return dict(far=_far(P), mid=_mid(P), main=_main(P), fg=_fg(P))
