"""Локация «Сад на крыше» — рисованный фон (Skia) в нескольких освещениях.

Мир: 2600×1200 px. Пол крыши: y≈880–1100 (глубина), парапет: y≈640. Фон кэшируется в PNG по пресету.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, poly_path, Draw, shade, mix, rgb, gradient_rect, radial, ellipse_pts, noise_image, col

WW, WH = 2600, 1200
FLOOR_Y = 860

PRESETS = {
    "morning": dict(sky=[((150, 206, 236), 0.0), ((196, 228, 240), 0.55), ((255, 228, 196), 1.0)], sun=(420, 380, (255, 236, 190)),
                    far=(160, 190, 214), mid=(196, 168, 150), light=(255, 236, 206), amb=1.0, lit_windows=0.0, cloud=(255, 255, 255), wet=0.0),
    "day": dict(sky=[((116, 190, 238), 0.0), ((170, 216, 240), 0.6), ((226, 240, 246), 1.0)], sun=(700, 220, (255, 250, 220)),
                far=(150, 184, 210), mid=(200, 170, 150), light=(255, 248, 230), amb=1.05, lit_windows=0.0, cloud=(255, 255, 255), wet=0.0),
    "evening": dict(sky=[((84, 70, 140), 0.0), ((218, 108, 120), 0.55), ((255, 178, 102), 1.0)], sun=(2100, 560, (255, 190, 120)),
                    far=(120, 90, 130), mid=(150, 110, 120), light=(255, 180, 130), amb=0.82, lit_windows=1.0, cloud=(255, 190, 170), wet=0.0),
    "storm": dict(sky=[((36, 44, 66), 0.0), ((70, 82, 108), 0.6), ((104, 112, 132), 1.0)], sun=None,
                  far=(78, 88, 110), mid=(90, 94, 110), light=(170, 182, 210), amb=0.62, lit_windows=0.8, cloud=(120, 128, 150), wet=0.6),
    "after_rain": dict(sky=[((92, 182, 240), 0.0), ((150, 214, 246), 0.6), ((232, 246, 250), 1.0)], sun=(560, 300, (255, 252, 230)),
                       far=(150, 190, 220), mid=(206, 176, 156), light=(255, 252, 236), amb=1.1, lit_windows=0.0, cloud=(255, 255, 255), wet=1.0),
}


def lit(c, P, k=1.0):
    """Окрасить цвет светом пресета."""
    L = rgb(P["light"])
    r, g, b = rgb(c)
    a = P["amb"] * k
    return (min(255, r * a * (0.75 + 0.25 * L[0] / 255)), min(255, g * a * (0.75 + 0.25 * L[1] / 255)), min(255, b * a * (0.75 + 0.25 * L[2] / 255)))


def cloud(c, x, y, s, color, alpha=0.9):
    for dx, dy, r in ((0, 0, 1.0), (0.9, 0.15, 0.75), (-0.9, 0.2, 0.7), (0.4, -0.35, 0.7), (-0.35, -0.3, 0.6), (1.6, 0.3, 0.5), (-1.6, 0.35, 0.45)):
        c.drawCircle(x + dx * s, y + dy * s, r * s, paint(color, alpha, blur=s * 0.08))
    c.drawOval(skia.Rect(x - 2.0 * s, y + 0.2 * s, x + 2.0 * s, y + 0.75 * s), paint(shade(color, 0.92), alpha * 0.6, blur=s * 0.15))


def buildings(c, base_y, color, rng, n, hmin, hmax, wmin, wmax, windows=0.0, win_col=(255, 220, 150), x0=-50, x1=WW + 50, top_details=True):
    x = x0
    while x < x1:
        w = rng.uniform(wmin, wmax)
        h = rng.uniform(hmin, hmax)
        r = skia.Rect(x, base_y - h, x + w, base_y + 400)
        c.drawRect(r, paint(color))
        if top_details and rng.random() < 0.4:
            c.drawRect(skia.Rect(x + w * 0.2, base_y - h - 18, x + w * 0.35, base_y - h), paint(color))
        if top_details and rng.random() < 0.3:
            c.drawRect(skia.Rect(x + w * 0.6, base_y - h - 40, x + w * 0.62, base_y - h), paint(color))
        if windows > 0:
            for wy in np.arange(base_y - h + 14, base_y, 22):
                for wx in np.arange(x + 8, x + w - 10, 18):
                    if rng.random() < 0.45 * windows:
                        c.drawRect(skia.Rect(wx, wy, wx + 7, wy + 10), paint(win_col, 0.85))
        x += w + rng.uniform(-4, 10)


def mosque(c, x, base, color, s=1.0):
    D = Draw(c)
    c.drawRect(skia.Rect(x - 60 * s, base - 90 * s, x + 60 * s, base), paint(color))
    dome = smooth_path([(x - 52 * s, base - 88 * s), (x - 40 * s, base - 140 * s), (x, base - 165 * s), (x + 40 * s, base - 140 * s), (x + 52 * s, base - 88 * s)], tension=0.6)
    c.drawPath(dome, paint(color))
    c.drawRect(skia.Rect(x - 1.5 * s, base - 190 * s, x + 1.5 * s, base - 160 * s), paint(color))
    c.drawCircle(x, base - 192 * s, 5 * s, paint(color))
    mx = x + 95 * s
    c.drawRect(skia.Rect(mx - 9 * s, base - 260 * s, mx + 9 * s, base), paint(color))
    c.drawRect(skia.Rect(mx - 14 * s, base - 200 * s, mx + 14 * s, base - 192 * s), paint(color))
    c.drawPath(poly_path([(mx - 10 * s, base - 260 * s), (mx, base - 300 * s), (mx + 10 * s, base - 260 * s)]), paint(color))


def brick_wall(c, x0, x1, y0, y1, base, P):
    c.drawRect(skia.Rect(x0, y0, x1, y1), paint(lit(base, P)))
    rng = np.random.default_rng(4)
    bh, bw = 22, 58
    for row, yy in enumerate(np.arange(y0, y1, bh)):
        off = (row % 2) * bw / 2
        for xx in np.arange(x0 - off, x1, bw):
            k = rng.uniform(0.88, 1.06)
            c.drawRect(skia.Rect(xx + 2, yy + 2, xx + bw - 2, yy + bh - 2), paint(lit(shade(base, k), P)))
    # затенение к низу
    gradient_rect(c, (x0, y0, x1, y1), [((0, 0, 0, 0), 0.0), ((40, 20, 30, 70), 1.0)])


def planter(c, x, y, w, h, P, plants="herbs", seed=1):
    D = Draw(c)
    rng = np.random.default_rng(seed)
    wood = (168, 112, 72)
    box = poly_path([(x, y), (x + w, y), (x + w - 8, y + h), (x + 8, y + h)])
    D.shape(box, lit(wood, P), line=lit(shade(wood, 0.55), P), lw=2.5, shadow=(-10, -6, lit(shade(wood, 0.78), P), 6))
    for k in range(1, 3):
        D.stroke([(x + 6, y + h * k / 3), (x + w - 6, y + h * k / 3)], lit(shade(wood, 0.7), P), 2)
    c.drawRect(skia.Rect(x + 4, y - 6, x + w - 4, y + 4), paint(lit((96, 66, 48), P)))
    if plants == "tomato":
        for i in range(int(w / 70)):
            px = x + 30 + i * 70
            D.stroke([(px, y), (px + 4, y - 150)], lit((120, 90, 60), P), 3)
            for j in range(7):
                lx, ly = px + rng.uniform(-30, 30), y - rng.uniform(20, 160)
                c.drawOval(skia.Rect(lx - 16, ly - 9, lx + 16, ly + 9), paint(lit((70 + rng.integers(0, 30), 140, 70), P)))
            for j in range(3):
                tx, ty = px + rng.uniform(-22, 22), y - rng.uniform(40, 130)
                c.drawCircle(tx, ty, 9, paint(lit((222, 60, 50), P)))
                c.drawCircle(tx - 3, ty - 3, 3, paint((255, 255, 255), 0.5))
    else:
        for i in range(int(w / 16)):
            px = x + 10 + i * 16 + rng.uniform(-4, 4)
            hgt = rng.uniform(30, 70)
            gcol = lit((80 + rng.integers(0, 40), 150 + rng.integers(0, 40), 80), P)
            D.tapered([(px, y), (px + rng.uniform(-8, 8), y - hgt * 0.6), (px + rng.uniform(-14, 14), y - hgt)], 7, 1, gcol)
        if plants == "flowers":
            for i in range(int(w / 40)):
                fx, fy = x + 20 + i * 40 + rng.uniform(-8, 8), y - rng.uniform(40, 75)
                pc = [(250, 120, 140), (255, 210, 80), (180, 140, 240), (255, 255, 255)][i % 4]
                for k in range(5):
                    a = k * 1.2566
                    c.drawCircle(fx + math.cos(a) * 7, fy + math.sin(a) * 7, 6, paint(lit(pc, P)))
                c.drawCircle(fx, fy, 4, paint(lit((240, 180, 60), P)))


def clay_pot(c, x, y, s, P, color=(198, 108, 72)):
    D = Draw(c)
    body = poly_path([(x - 40 * s, y - 70 * s), (x + 40 * s, y - 70 * s), (x + 30 * s, y), (x - 30 * s, y)])
    D.shape(body, lit(color, P), line=lit(shade(color, 0.55), P), lw=2.5, shadow=(-8 * s, -4 * s, lit(shade(color, 0.75), P), 5))
    rim = skia.Rect(x - 46 * s, y - 84 * s, x + 46 * s, y - 66 * s)
    c.drawRoundRect(rim, 6, 6, paint(lit(shade(color, 1.08), P)))
    c.drawRoundRect(rim, 6, 6, paint(lit(shade(color, 0.55), P), style="stroke", width=2.5))
    c.drawOval(skia.Rect(x - 40 * s, y - 82 * s, x + 40 * s, y - 70 * s), paint(lit((92, 62, 44), P)))


def bench(c, x, y, P):
    D = Draw(c)
    wood = (186, 126, 80)
    for lx in (x + 18, x + 252):
        c.drawRect(skia.Rect(lx, y - 70, lx + 14, y), paint(lit((70, 64, 66), P)))
    for k, yy in enumerate((y - 82, y - 70)):
        r = skia.Rect(x, yy, x + 284, yy + 12)
        c.drawRoundRect(r, 4, 4, paint(lit(shade(wood, 1 - 0.06 * k), P)))
        c.drawRoundRect(r, 4, 4, paint(lit(shade(wood, 0.55), P), style="stroke", width=2))
    for k, yy in enumerate((y - 150, y - 128)):
        r = skia.Rect(x + 8, yy, x + 276, yy + 14)
        c.drawRoundRect(r, 4, 4, paint(lit(wood, P)))
        c.drawRoundRect(r, 4, 4, paint(lit(shade(wood, 0.55), P), style="stroke", width=2))
    for lx in (x + 20, x + 252):
        c.drawRect(skia.Rect(lx, y - 154, lx + 10, y - 80), paint(lit((70, 64, 66), P)))
    # подушка
    pil = smooth_path(ellipse_pts(x + 220, y - 98, 34, 16, 14))
    D.shape(pil, lit((230, 120, 110), P), line=lit((150, 70, 70), P), lw=2)


def kiosk(c, x, y, P, door_open=0.0):
    """Будка выхода на крышу с дверью (бабушка выходит)."""
    D = Draw(c)
    wall = (232, 214, 186)
    body = skia.Rect(x, y - 330, x + 260, y)
    c.drawRect(body, paint(lit(wall, P)))
    roof = poly_path([(x - 20, y - 330), (x + 280, y - 330), (x + 260, y - 360), (x, y - 360)])
    c.drawPath(roof, paint(lit((150, 80, 66), P)))
    dr = skia.Rect(x + 60, y - 250, x + 180, y)
    c.drawRect(dr, paint(lit((60, 44, 40), P)))
    w = 120 * (1 - door_open * 0.85)
    door = skia.Rect(x + 60, y - 250, x + 60 + w, y)
    c.drawRect(door, paint(lit((96, 150, 170), P)))
    c.drawRect(door, paint(lit((50, 80, 96), P), style="stroke", width=3))
    c.drawCircle(x + 60 + w - 14, y - 120, 6, paint(lit((240, 200, 90), P)))
    c.drawRect(skia.Rect(x + 200, y - 270, x + 245, y - 210), paint(lit((150, 200, 220), P)))
    c.drawRect(skia.Rect(x + 200, y - 270, x + 245, y - 210), paint(lit((80, 60, 50), P), style="stroke", width=3))
    gradient_rect(c, (x, y - 330, x + 260, y), [((0, 0, 0, 0), 0.0), ((40, 20, 30, 60), 1.0)])


def render_static(preset, seed=3):
    """Статичный фон без персонажей и анимируемых объектов -> skia.Image (2600×1200)."""
    P = PRESETS[preset]
    surf = skia.Surface(WW, WH)
    c = surf.getCanvas()
    D = Draw(c)
    rng = np.random.default_rng(seed)
    gradient_rect(c, (0, 0, WW, 700), P["sky"])
    if P["sun"]:
        sx, sy, sc = P["sun"]
        radial(c, sx, sy, 520, [(sc, 0.75, 0.0), (sc, 0.25, 0.35), (sc, 0.0, 1.0)])
        c.drawCircle(sx, sy, 62, paint(sc, 0.95, blur=6))
    cl = P["cloud"]
    for i in range(7):
        cloud(c, rng.uniform(0, WW), rng.uniform(90, 330), rng.uniform(40, 80), cl, 0.75 if preset != "storm" else 0.95)
    if preset == "storm":
        for i in range(9):
            cloud(c, rng.uniform(0, WW), rng.uniform(40, 360), rng.uniform(70, 130), shade(cl, 0.8), 0.95)
    # дальний город (воздушная перспектива)
    far = P["far"]
    buildings(c, 640, mix(far, P["sky"][-1][0], 0.45), np.random.default_rng(11), 40, 60, 200, 60, 140, windows=0.3 * P["lit_windows"])
    mosque(c, 1880, 600, mix(far, P["sky"][-1][0], 0.35), 0.9)
    buildings(c, 660, mix(far, P["sky"][-1][0], 0.15), np.random.default_rng(12), 30, 40, 140, 80, 180, windows=0.6 * P["lit_windows"])
    # деревья между домами
    for i in range(14):
        tx = rng.uniform(0, WW)
        c.drawCircle(tx, 660 - rng.uniform(0, 30), rng.uniform(26, 50), paint(lit((90, 140, 96), P, 0.85), 0.9))
    # соседняя крыша: бак, антенны, бельё
    mid = P["mid"]
    c.drawRect(skia.Rect(1980, 520, 2560, 700), paint(lit(mid, P, 0.9)))
    c.drawRect(skia.Rect(2080, 420, 2200, 525), paint(lit((150, 160, 170), P)))
    c.drawOval(skia.Rect(2080, 400, 2200, 440), paint(lit((170, 180, 190), P)))
    for ax in (2260, 2340):
        D.stroke([(ax, 520), (ax, 410)], lit((80, 80, 90), P), 3)
        D.stroke([(ax - 30, 440), (ax + 30, 440)], lit((80, 80, 90), P), 3)
    # наша крыша: парапет (кирпич) с плиткой-отливом
    brick_wall(c, -20, WW + 20, 640, 760, (196, 112, 90), P)
    c.drawRect(skia.Rect(-20, 628, WW + 20, 648), paint(lit((214, 206, 196), P)))
    c.drawRect(skia.Rect(-20, 646, WW + 20, 652), paint(lit((120, 100, 96), P), 0.5))
    # перила-решётка поверх парапета
    for xx in range(0, WW, 36):
        D.stroke([(xx, 628), (xx, 560)], lit((70, 76, 86), P), 3)
    D.stroke([(-20, 560), (WW + 20, 560)], lit((70, 76, 86), P), 5)
    # гирлянда
    pts = [(x, 470 + 40 * math.sin((x / WW) * math.pi * 3) ** 2) for x in range(0, WW, 40)]
    D.stroke(pts, lit((60, 50, 50), P), 2)
    # шпалера с вьюнком
    for xx in range(1480, 1800, 40):
        D.stroke([(xx, 760), (xx, 520)], lit((150, 110, 70), P), 4)
    for yy in range(540, 760, 40):
        D.stroke([(1470, yy), (1810, yy)], lit((150, 110, 70), P), 3)
    for i in range(90):
        lx, ly = 1480 + rng.uniform(0, 320), 520 + rng.uniform(0, 240)
        c.drawOval(skia.Rect(lx - 13, ly - 8, lx + 13, ly + 8), paint(lit((70 + rng.integers(0, 40), 150, 80), P)))
        if rng.random() < 0.15:
            c.drawCircle(lx, ly, 6, paint(lit((240, 150, 200), P)))
    # пол крыши
    floor = (196, 184, 168)
    gradient_rect(c, (0, 760, WW, WH), [(lit(shade(floor, 0.92), P), 0.0), (lit(floor, P), 0.4), (lit(shade(floor, 0.85), P), 1.0)])
    for k, yy in enumerate([768, 790, 818, 852, 894, 944, 1004, 1074, 1160]):
        D.stroke([(-20, yy), (WW + 20, yy)], lit(shade(floor, 0.8), P), 1.6 + k * 0.25)
    vp = (1300, 300)
    for xx in range(-1400, 4000, 150):
        D.stroke([(vp[0] + (xx - vp[0]) * 0.32, 768), (xx, WH)], lit(shade(floor, 0.84), P), 1.4)
    # тень от парапета на полу
    gradient_rect(c, (0, 760, WW, 800), [((30, 20, 40, 70), 0.0), ((30, 20, 40, 0), 1.0)])
    if P["wet"] > 0:  # лужи с отражением неба
        for i in range(9):
            px, py = rng.uniform(100, WW - 100), rng.uniform(820, 1150)
            rx = rng.uniform(60, 160)
            c.drawOval(skia.Rect(px - rx, py - rx * 0.12, px + rx, py + rx * 0.12), paint(P["sky"][1][0], 0.55 * P["wet"]))
            c.drawOval(skia.Rect(px - rx * 0.6, py - rx * 0.05, px + rx * 0.2, py), paint((255, 255, 255), 0.25 * P["wet"]))
    # грядки и горшки у парапета
    planter(c, 60, 700, 360, 70, P, "tomato", 1)
    planter(c, 470, 712, 260, 60, P, "flowers", 2)
    planter(c, 1860, 712, 300, 60, P, "herbs", 3)
    planter(c, 2200, 700, 340, 70, P, "tomato", 4)
    for i, (px, s) in enumerate(((800, 0.7), (870, 0.55), (2600 - 60, 0.8))):
        clay_pot(c, px, 760, s, P)
        for k in range(6):
            a = -math.pi / 2 + (k - 2.5) * 0.4
            D.tapered([(px, 760 - 66 * s), (px + math.cos(a) * 60 * s, 760 - 66 * s + math.sin(a) * 60 * s)], 10 * s, 2 * s, lit((70, 150, 80), P))
    # водосточная бочка
    c.drawRoundRect(skia.Rect(1390, 650, 1460, 770), 10, 10, paint(lit((80, 130, 170), P)))
    c.drawRoundRect(skia.Rect(1390, 650, 1460, 770), 10, 10, paint(lit((40, 70, 96), P), style="stroke", width=3))
    # шланг
    D.stroke([(1460, 760), (1500, 790), (1440, 810), (1390, 795), (1420, 780)], lit((60, 150, 90), P), 6)
    # зерно бумаги
    img = noise_image(WW, WH, seed=seed, strength=6)
    c.drawImage(img, 0, 0)
    return surf.makeImageSnapshot()


def draw_lights(c, P, t):
    """Огоньки гирлянды (мерцают вечером/в грозу)."""
    on = 0.4 + 0.6 * P["lit_windows"]
    for i, x in enumerate(range(20, WW, 80)):
        y = 470 + 40 * math.sin((x / WW) * math.pi * 3) ** 2 + 8
        cc = [(255, 210, 120), (255, 150, 150), (150, 220, 255)][i % 3]
        a = on * (0.75 + 0.25 * math.sin(t * 3 + i))
        c.drawCircle(x, y, 7, paint(cc, a))
        if P["lit_windows"] > 0.3:
            c.drawCircle(x, y, 22, paint(cc, 0.25 * a, blur=10))
