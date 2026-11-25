"""Общая библиотека окружения семейного дома: свет и время суток, окна со шторами, растения, мебель,
текстуры, мягкий свет из окна, контактные тени. Все локации строятся из этих деталей.

Пресет света P: light — цвет света, amb — общая яркость, warm — тёплая доля, sky — градиент неба в окне/над двором.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, poly_path, Draw, shade, mix, rgb, gradient_rect, radial, ellipse_pts, noise_image, col

LIGHT = {
    "morning": dict(light=(255, 238, 212), amb=1.0, sky=[((156, 208, 238), 0.0), ((204, 230, 242), 0.55), ((255, 232, 204), 1.0)],
                    sun=(0.2, (255, 238, 196)), win=0.0, beam=0.55, tint=((255, 226, 180), 0.05)),
    "day": dict(light=(255, 250, 236), amb=1.04, sky=[((120, 192, 238), 0.0), ((172, 218, 242), 0.6), ((230, 242, 246), 1.0)],
                sun=(0.35, (255, 250, 222)), win=0.0, beam=0.45, tint=((255, 252, 236), 0.03)),
    "golden": dict(light=(255, 200, 150), amb=0.90, sky=[((120, 120, 180), 0.0), ((236, 150, 140), 0.55), ((255, 196, 130), 1.0)],
                   sun=(0.85, (255, 200, 130)), win=0.7, beam=0.6, tint=((255, 150, 100), 0.08)),
    "windy": dict(light=(214, 222, 236), amb=0.80, sky=[((112, 126, 156), 0.0), ((150, 160, 184), 0.6), ((186, 192, 206), 1.0)],
                  sun=None, win=0.5, beam=0.0, tint=((120, 140, 190), 0.10)),
    "night": dict(light=(150, 160, 220), amb=0.62, sky=[((30, 36, 80), 0.0), ((54, 60, 112), 0.6), ((90, 84, 130), 1.0)],
                  sun=None, win=1.0, beam=0.0, tint=((60, 70, 150), 0.14)),
    "lamp": dict(light=(255, 214, 170), amb=0.88, sky=[((70, 64, 120), 0.0), ((170, 110, 130), 0.6), ((240, 160, 120), 1.0)],
                 sun=None, win=1.0, beam=0.0, tint=((255, 170, 110), 0.07)),
}


def lit(c, P, k=1.0):
    L = rgb(P["light"])
    r, g, b = rgb(c)
    a = P["amb"] * k
    return (min(255, r * a * (0.72 + 0.28 * L[0] / 255)), min(255, g * a * (0.72 + 0.28 * L[1] / 255)), min(255, b * a * (0.72 + 0.28 * L[2] / 255)))


def box(c, x0, y0, x1, y1, fill, P, line=True, r=6, shadow=True, k=1.0):
    D = Draw(c)
    p = skia.Path(); p.addRoundRect(skia.Rect(x0, y0, x1, y1), r, r)
    D.shape(p, lit(fill, P, k), line=lit(shade(fill, 0.6), P) if line else None, lw=2.2,
            shadow=(-(x1 - x0) * 0.06, -(y1 - y0) * 0.05, lit(shade(fill, 0.84), P, k), 6) if shadow else None)
    return p


def contact(c, x, y, w, alpha=0.28, h=None):
    c.drawOval(skia.Rect(x - w / 2, y - (h or w * 0.07), x + w / 2, y + (h or w * 0.07)), paint((50, 34, 40), alpha, blur=max(4, w * 0.05)))


def planks(c, x0, y0, x1, y1, P, base=(208, 160, 112), vp=None, n=26):
    """Деревянный пол в перспективе: доски сходятся к точке схода vp."""
    D = Draw(c)
    gradient_rect(c, (x0, y0, x1, y1), [(lit(shade(base, 0.82), P), 0.0), (lit(base, P), 0.5), (lit(shade(base, 0.92), P), 1.0)])
    vp = vp or ((x0 + x1) / 2, y0 - 700)
    rng = np.random.default_rng(3)
    span = (x1 - x0) * 2.2
    for i in range(n * 2):
        xb = x0 - span * 0.3 + span * i / (n * 2)
        xt = vp[0] + (xb - vp[0]) * (y0 - vp[1]) / (y1 - vp[1])
        D.stroke([(xt, y0), (xb, y1)], lit(shade(base, 0.78), P), 1.6, alpha=0.7)
    for i in range(60):  # стыки досок
        yy = y0 + (y1 - y0) * (rng.random() ** 1.6)
        xx = rng.uniform(x0, x1)
        D.stroke([(xx, yy), (xx + 6, yy + 18 * (yy - y0) / (y1 - y0) + 4)], lit(shade(base, 0.74), P), 1.2, alpha=0.6)
    gradient_rect(c, (x0, y0, x1, y0 + 50), [((40, 26, 30, 80), 0.0), ((40, 26, 30, 0), 1.0)])


def wall(c, x0, y0, x1, y1, P, color, wainscot=None, wy=None, pattern=None):
    gradient_rect(c, (x0, y0, x1, y1), [(lit(shade(color, 0.96), P), 0.0), (lit(color, P), 0.6), (lit(shade(color, 0.94), P), 1.0)])
    if pattern == "dots":
        rng = np.random.default_rng(7)
        for yy in range(int(y0) + 30, int(wy or y1) - 10, 60):
            for xx in range(int(x0) + ((yy // 60) % 2) * 30, int(x1), 60):
                c.drawCircle(xx, yy, 3.2, paint(lit(shade(color, 0.9), P), 0.8))
    elif pattern == "stripes":
        for xx in range(int(x0), int(x1), 44):
            c.drawRect(skia.Rect(xx, y0, xx + 16, wy or y1), paint(lit(shade(color, 1.04), P), 0.6))
    if wainscot is not None:
        c.drawRect(skia.Rect(x0, wy, x1, y1), paint(lit(wainscot, P)))
        for xx in range(int(x0) + 20, int(x1), 120):
            c.drawRoundRect(skia.Rect(xx, wy + 22, xx + 96, y1 - 20), 4, 4, paint(lit(shade(wainscot, 0.88), P), style="stroke", width=2))
        c.drawRect(skia.Rect(x0, wy - 8, x1, wy + 4), paint(lit(shade(wainscot, 1.08), P)))
        c.drawRect(skia.Rect(x0, wy + 4, x1, wy + 8), paint(lit(shade(wainscot, 0.7), P), 0.6))
    c.drawRect(skia.Rect(x0, y1 - 18, x1, y1), paint(lit((236, 228, 216), P)))  # плинтус


def window(c, x0, y0, x1, y1, P, view=None, curtain=(240, 180, 170), frame=(250, 248, 242), sill_plants=True, open_curtains=0.75, seed=1, inside=False):
    """Окно с видом (view(c, rect)), рамой, шторами и подоконником с цветами."""
    D = Draw(c)
    c.save()
    c.clipRect(skia.Rect(x0, y0, x1, y1))
    if view:
        view(c, (x0, y0, x1, y1))
    else:
        gradient_rect(c, (x0, y0, x1, y1), P["sky"])
    c.drawRect(skia.Rect(x0, y0, x1, y1), paint((255, 255, 255), 0.10))
    c.restore()
    fw = 14
    for r in ((x0 - fw, y0 - fw, x1 + fw, y0), (x0 - fw, y1, x1 + fw, y1 + fw), (x0 - fw, y0, x0, y1), (x1, y0, x1 + fw, y1),
              ((x0 + x1) / 2 - 5, y0, (x0 + x1) / 2 + 5, y1), (x0, (y0 + y1) * 0.42 - 4, x1, (y0 + y1) * 0.42 + 4)):
        c.drawRect(skia.Rect(*r), paint(lit(frame, P)))
    c.drawRect(skia.Rect(x0 - fw, y0 - fw, x1 + fw, y1 + fw), paint(lit(shade(frame, 0.7), P), style="stroke", width=2))
    # подоконник
    c.drawRoundRect(skia.Rect(x0 - 40, y1 + fw, x1 + 40, y1 + fw + 18), 4, 4, paint(lit(shade(frame, 0.98), P)))
    c.drawRect(skia.Rect(x0 - 40, y1 + fw + 18, x1 + 40, y1 + fw + 26), paint(lit(shade(frame, 0.7), P), 0.5))
    if sill_plants:
        rng = np.random.default_rng(seed)
        for k, px in enumerate(np.linspace(x0 + 40, x1 - 40, 3)):
            plant_pot(c, px, y1 + fw, 0.55 + 0.15 * rng.random(), P, kind=["herb", "flower", "succulent"][k % 3], seed=seed + k)
    # шторы с мягкими складками
    if inside:
        c.save(); c.clipRect(skia.Rect(x0, y0, x1, y1))
    cw = (x1 - x0) * 0.5 * (1 - open_curtains) + 70
    for side in (-1, 1):
        xe = x0 - 30 if side < 0 else x1 + 30
        xi = xe - side * cw
        pts = [(xe, y0 - 40), (xi, y0 - 40), (xi + side * 20, (y0 + y1) / 2), (xi - side * 10, y1 + 60), (xe, y1 + 70)]
        cur = smooth_path(pts, tension=0.35)
        D.shape(cur, lit(curtain, P), line=lit(shade(curtain, 0.62), P), lw=2, shadow=(side * 18, 0, lit(shade(curtain, 0.84), P), 10))
        c.save(); c.clipPath(cur, skia.ClipOp.kIntersect, True)
        for k in range(4):
            xx = xe - side * cw * (0.2 + 0.22 * k)
            D.stroke([(xx, y0 - 40), (xx + side * 6, (y0 + y1) / 2), (xx - side * 4, y1 + 70)], lit(shade(curtain, 0.82), P), 3, alpha=0.6)
        c.restore()
        # подхват
        c.drawRoundRect(skia.Rect(xi - 18 if side < 0 else xi - 4, (y0 + y1) * 0.58 - 5, xi + 4 if side < 0 else xi + 18, (y0 + y1) * 0.58 + 5), 3, 3, paint(lit((210, 170, 90), P)))
    if inside:
        c.restore()
        return
    c.drawRoundRect(skia.Rect(x0 - 70, y0 - 52, x1 + 70, y0 - 40), 6, 6, paint(lit((160, 120, 84), P)))


def plant_pot(c, x, y, s, P, kind="herb", seed=1, pot=(206, 120, 86)):
    D = Draw(c)
    rng = np.random.default_rng(seed)
    body = poly_path([(x - 30 * s, y - 52 * s), (x + 30 * s, y - 52 * s), (x + 22 * s, y), (x - 22 * s, y)])
    D.shape(body, lit(pot, P), line=lit(shade(pot, 0.55), P), lw=2, shadow=(-6 * s, -4 * s, lit(shade(pot, 0.78), P), 4))
    c.drawRoundRect(skia.Rect(x - 34 * s, y - 62 * s, x + 34 * s, y - 50 * s), 4, 4, paint(lit(shade(pot, 1.06), P)))
    top = y - 60 * s
    if kind == "herb":
        for k in range(11):
            a = -math.pi / 2 + rng.uniform(-1.1, 1.1)
            L = rng.uniform(40, 80) * s
            tip = (x + math.cos(a) * L, top + math.sin(a) * L)
            D.stroke([(x, top), tip], lit((70, 140, 70), P), 2)
            D.ellipse(tip[0], tip[1], 9 * s, 6 * s, lit((96, 176, 90), P), rot=a)
    elif kind == "flower":
        for k in range(7):
            a = -math.pi / 2 + rng.uniform(-0.9, 0.9)
            L = rng.uniform(40, 70) * s
            tip = (x + math.cos(a) * L, top + math.sin(a) * L)
            D.stroke([(x, top), tip], lit((70, 140, 70), P), 2)
            D.ellipse((x + tip[0]) / 2 + 8 * s, (top + tip[1]) / 2, 10 * s, 5 * s, lit((96, 170, 90), P), rot=a)
            for q in range(5):
                b = q * 1.256
                c.drawCircle(tip[0] + math.cos(b) * 6 * s, tip[1] + math.sin(b) * 6 * s, 5 * s, paint(lit((250, 150, 170), P)))
            c.drawCircle(tip[0], tip[1], 3.5 * s, paint(lit((255, 220, 110), P)))
    elif kind == "succulent":
        for k in range(9):
            a = -math.pi / 2 + (k - 4) * 0.32
            L = (38 - abs(k - 4) * 5) * s
            pth = smooth_path([(x - 6 * s, top), (x + math.cos(a) * L - 6 * s, top + math.sin(a) * L), (x + 6 * s, top)], tension=0.5)
            D.shape(pth, lit((130, 186, 150), P), line=lit((70, 120, 90), P), lw=1.5)
    elif kind == "big":
        for k in range(9):
            a = -math.pi / 2 + rng.uniform(-1.2, 1.2)
            L = rng.uniform(110, 190) * s
            tip = (x + math.cos(a) * L, top + math.sin(a) * L)
            D.stroke([(x, top), ((x + tip[0]) / 2, (top + tip[1]) / 2 - 10 * s), tip], lit((70, 130, 70), P), 3)
            lf = smooth_path([(tip[0], tip[1]), (tip[0] + 40 * s, tip[1] - 22 * s), (tip[0] + 70 * s * math.cos(a + 0.4), tip[1] + 40 * s * math.sin(a)),
                              (tip[0] - 20 * s, tip[1] + 25 * s)], tension=0.6)
            D.shape(lf, lit((84, 160, 96), P), line=lit((50, 110, 60), P), lw=1.8, shadow=(-5, -4, lit((64, 130, 76), P), 4))


def frame_pic(c, x, y, w, h, P, kind="sun", seed=1):
    """Рамка с детским рисунком (без текста)."""
    D = Draw(c)
    box(c, x - 8, y - 8, x + w + 8, y + h + 8, (176, 128, 90), P, r=3)
    c.drawRect(skia.Rect(x, y, x + w, y + h), paint(lit((252, 250, 244), P)))
    if kind == "sun":
        c.drawCircle(x + w * 0.7, y + h * 0.3, h * 0.16, paint(lit((255, 200, 60), P)))
        for k in range(8):
            a = k * 0.785
            D.stroke([(x + w * 0.7 + math.cos(a) * h * 0.2, y + h * 0.3 + math.sin(a) * h * 0.2),
                      (x + w * 0.7 + math.cos(a) * h * 0.28, y + h * 0.3 + math.sin(a) * h * 0.28)], lit((255, 180, 40), P), 2)
        D.stroke([(x + w * 0.1, y + h * 0.85), (x + w * 0.9, y + h * 0.85)], lit((90, 170, 90), P), 4)
        c.drawRect(skia.Rect(x + w * 0.18, y + h * 0.55, x + w * 0.45, y + h * 0.85), paint(lit((240, 120, 100), P)))
        c.drawPath(poly_path([(x + w * 0.14, y + h * 0.56), (x + w * 0.315, y + h * 0.38), (x + w * 0.49, y + h * 0.56)]), paint(lit((150, 90, 70), P)))
    elif kind == "flower":
        for k in range(6):
            a = k * 1.047
            c.drawCircle(x + w / 2 + math.cos(a) * h * 0.16, y + h * 0.4 + math.sin(a) * h * 0.16, h * 0.1, paint(lit((250, 140, 160), P)))
        c.drawCircle(x + w / 2, y + h * 0.4, h * 0.08, paint(lit((255, 210, 80), P)))
        D.stroke([(x + w / 2, y + h * 0.5), (x + w / 2, y + h * 0.92)], lit((80, 160, 80), P), 3)
    elif kind == "pattern":  # геометрический орнамент
        cx, cy, r = x + w / 2, y + h / 2, min(w, h) * 0.36
        for k in range(8):
            a = k * math.pi / 4
            pts = [(cx + math.cos(a + d) * r * m, cy + math.sin(a + d) * r * m) for d, m in ((0, 1.0), (0.39, 0.55), (0, 0.2), (-0.39, 0.55))]
            c.drawPath(poly_path(pts), paint(lit((80, 140, 150) if k % 2 else (210, 160, 80), P), 0.9))
        c.drawCircle(cx, cy, r * 0.18, paint(lit((240, 200, 120), P)))
    elif kind == "family":  # три фигурки — рисунок детей
        for k, (hx, hh, cc) in enumerate(((0.3, 0.55, (240, 170, 170)), (0.55, 0.62, (120, 170, 210)), (0.75, 0.68, (250, 210, 100)))):
            c.drawCircle(x + w * hx, y + h * (hh - 0.18) - (0.1 if k == 0 else 0) * h, h * 0.08, paint(lit((240, 200, 170), P)))
            c.drawPath(poly_path([(x + w * hx, y + h * (hh - 0.1)), (x + w * (hx - 0.08), y + h * 0.9), (x + w * (hx + 0.08), y + h * 0.9)]), paint(lit(cc, P)))
        c.drawCircle(x + w * 0.15, y + h * 0.18, h * 0.08, paint(lit((255, 200, 60), P)))


def books(c, x, y, w, h, P, seed=2):
    rng = np.random.default_rng(seed)
    xx = x
    cols = [(200, 110, 100), (110, 150, 190), (230, 190, 110), (130, 170, 130), (190, 140, 190), (240, 230, 210)]
    while xx < x + w - 10:
        bw = rng.uniform(12, 26)
        bh = h * rng.uniform(0.7, 1.0)
        cc = cols[rng.integers(0, len(cols))]
        c.drawRoundRect(skia.Rect(xx, y - bh, xx + bw, y), 2, 2, paint(lit(cc, P)))
        c.drawRect(skia.Rect(xx + 2, y - bh * 0.8, xx + bw - 2, y - bh * 0.74), paint(lit(shade(cc, 1.2), P), 0.7))
        xx += bw + 1.5


def cushion(c, x, y, w, h, color, P, rot=0.0, pattern=None):
    D = Draw(c)
    c.save(); c.translate(x, y); c.rotate(rot)
    pth = smooth_path([(-w / 2, -h / 2), (0, -h / 2 + 6), (w / 2, -h / 2), (w / 2 - 6, 0), (w / 2, h / 2), (0, h / 2 - 6), (-w / 2, h / 2), (-w / 2 + 6, 0)], tension=0.5)
    D.shape(pth, lit(color, P), line=lit(shade(color, 0.6), P), lw=2, shadow=(-w * 0.12, -h * 0.12, lit(shade(color, 0.82), P), 8),
            light=(w * 0.05, h * 0.06, (255, 255, 255), 6))
    if pattern == "dots":
        for k in range(5):
            c.drawCircle(-w * 0.25 + k * w * 0.12, (k % 2) * h * 0.15 - h * 0.05, 4, paint(lit(shade(color, 1.18), P)))
    c.restore()


def rug(c, cx, cy, rx, ry, P, color=(196, 120, 110), border=(240, 214, 160)):
    c.drawOval(skia.Rect(cx - rx, cy - ry, cx + rx, cy + ry), paint(lit(border, P)))
    c.drawOval(skia.Rect(cx - rx * 0.9, cy - ry * 0.86, cx + rx * 0.9, cy + ry * 0.86), paint(lit(color, P)))
    c.drawOval(skia.Rect(cx - rx * 0.6, cy - ry * 0.55, cx + rx * 0.6, cy + ry * 0.55), paint(lit(shade(color, 1.12), P), style="stroke", width=5))
    c.drawOval(skia.Rect(cx - rx * 0.3, cy - ry * 0.25, cx + rx * 0.3, cy + ry * 0.25), paint(lit(border, P), 0.8))


def sunbeam(c, x0, y0, x1, y1, P, floor_y, spread=1.6, alpha=None):
    """Мягкий луч из окна и пятно света на полу (добавочное смешивание)."""
    a = P["beam"] if alpha is None else alpha
    if a <= 0:
        return
    w = x1 - x0
    shift = (floor_y - y1) * 0.55
    poly = poly_path([(x0, y0), (x1, y0), (x1 + shift + w * (spread - 1), floor_y + 60), (x0 + shift, floor_y + 60)])
    p = paint(P["light"], 0.16 * a, blur=26)
    p.setBlendMode(skia.BlendMode.kScreen)
    c.drawPath(poly, p)
    p2 = paint(P["light"], 0.30 * a, blur=18)
    p2.setBlendMode(skia.BlendMode.kScreen)
    c.drawPath(poly_path([(x0 + shift, floor_y + 10), (x1 + shift + w * (spread - 1), floor_y + 10),
                          (x1 + shift * 1.35 + w * (spread - 1), floor_y + 160), (x0 + shift * 1.35, floor_y + 160)]), p2)


def lamp_glow(c, x, y, r, P, k=1.0):
    p = paint((255, 214, 150), 0.0)
    shader = skia.GradientShader.MakeRadial(skia.Point(x, y), r, [col((255, 220, 160), 0.55 * k), col((255, 200, 140), 0.0)], [0.0, 1.0])
    p = skia.Paint(AntiAlias=True); p.setShader(shader); p.setBlendMode(skia.BlendMode.kScreen)
    c.drawCircle(x, y, r, p)


def grain(c, w, h, seed=1, strength=6):
    c.drawImage(noise_image(w, h, seed=seed, strength=strength), 0, 0)


def cloud(c, x, y, s, color, alpha=0.9):
    for dx, dy, r in ((0, 0, 1.0), (0.9, 0.15, 0.75), (-0.9, 0.2, 0.7), (0.4, -0.35, 0.7), (-0.35, -0.3, 0.6), (1.6, 0.3, 0.5), (-1.6, 0.35, 0.45)):
        c.drawCircle(x + dx * s, y + dy * s, r * s, paint(color, alpha, blur=s * 0.08))
    c.drawOval(skia.Rect(x - 2.0 * s, y + 0.2 * s, x + 2.0 * s, y + 0.75 * s), paint(shade(color, 0.93), alpha * 0.6, blur=s * 0.15))


def tree(c, x, y, s, P, seed=1, apples=0, dark=1.0):
    """Лиственное дерево: ствол с ветвями и пышная крона из облаков листвы со светотенью."""
    D = Draw(c)
    rng = np.random.default_rng(seed)
    bark = lit((128, 92, 70), P, dark)
    trunk = smooth_path([(x - 26 * s, y), (x - 18 * s, y - 160 * s), (x - 40 * s, y - 300 * s), (x - 10 * s, y - 330 * s), (x + 4 * s, y - 230 * s),
                         (x + 40 * s, y - 320 * s), (x + 60 * s, y - 300 * s), (x + 20 * s, y - 160 * s), (x + 30 * s, y)], tension=0.4)
    D.shape(trunk, bark, line=shade(bark, 0.6), lw=2.4, shadow=(-14 * s, 0, shade(bark, 0.8), 6))
    blobs = [(rng.uniform(-170, 170) * s, rng.uniform(-560, -300) * s, rng.uniform(80, 140) * s) for _ in range(16)]
    base_g = (98, 158, 92)
    for dx, dy, r in sorted(blobs, key=lambda b: b[1]):
        c.drawCircle(x + dx, y + dy, r, paint(lit(shade(base_g, 0.78), P, dark)))
    for dx, dy, r in blobs:
        c.drawCircle(x + dx - r * 0.12, y + dy - r * 0.16, r * 0.82, paint(lit(base_g, P, dark)))
    for dx, dy, r in blobs[:9]:
        c.drawCircle(x + dx - r * 0.3, y + dy - r * 0.35, r * 0.42, paint(lit(shade(base_g, 1.18), P, dark), 0.8, blur=r * 0.1))
    for k in range(apples):
        dx, dy, r = blobs[k % len(blobs)]
        ax, ay = x + dx + rng.uniform(-0.5, 0.5) * r, y + dy + rng.uniform(-0.3, 0.5) * r
        c.drawCircle(ax, ay, 11 * s, paint(lit((226, 76, 64), P, dark)))
        c.drawCircle(ax - 3 * s, ay - 3 * s, 3.5 * s, paint((255, 255, 255), 0.6))


def bush(c, x, y, s, P, flowers=None, seed=1):
    rng = np.random.default_rng(seed)
    g = (92, 152, 88)
    blobs = [(rng.uniform(-80, 80) * s, rng.uniform(-90, -20) * s, rng.uniform(40, 70) * s) for _ in range(8)]
    for dx, dy, r in blobs:
        c.drawCircle(x + dx, y + dy, r, paint(lit(shade(g, 0.8), P)))
    for dx, dy, r in blobs:
        c.drawCircle(x + dx - r * 0.15, y + dy - r * 0.2, r * 0.78, paint(lit(g, P)))
    if flowers:
        for k in range(14):
            dx, dy, r = blobs[k % len(blobs)]
            fx, fy = x + dx + rng.uniform(-0.6, 0.6) * r, y + dy + rng.uniform(-0.6, 0.4) * r
            for q in range(5):
                b = q * 1.256
                c.drawCircle(fx + math.cos(b) * 5 * s, fy + math.sin(b) * 5 * s, 4.5 * s, paint(lit(flowers, P)))
            c.drawCircle(fx, fy, 3 * s, paint(lit((255, 236, 150), P)))
