"""Реквизит: предметы в руках (hold), подсолнух в горшке (стадии роста), голубь, частицы воды и дождя."""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, poly_path, Draw, shade, ellipse_pts, tube, rgb


def _rot(c, pos, ang):
    c.save(); c.translate(*pos); c.rotate(math.degrees(ang) - 90)


def watering_can(scale=1.0, tilt=0.0, color=(70, 160, 210)):
    def f(c, pos, ang, u):
        D = Draw(c)
        _rot(c, pos, ang)
        c.rotate(math.degrees(tilt))
        s = u * 0.55 * scale
        body = smooth_path([(-s * 0.45, s * 0.25), (s * 0.45, s * 0.25), (s * 0.5, s * 1.05), (-s * 0.5, s * 1.05)], tension=0.2)
        D.shape(body, color, line=shade(color, 0.5), lw=2.4, shadow=(-s * 0.08, -s * 0.06, shade(color, 0.8), s * 0.05))
        D.stroke([(-s * 0.3, s * 0.25), (0, -s * 0.05), (s * 0.3, s * 0.25)], shade(color, 0.55), s * 0.08)
        sp, _ = tube([(s * 0.45, s * 0.75), (s * 0.85, s * 0.45), (s * 1.1, s * 0.15)], [s * 0.14, s * 0.1, s * 0.08], n=10)
        D.shape(sp, color, line=shade(color, 0.5), lw=2)
        c.drawOval(skia.Rect(s * 1.02, s * 0.03, s * 1.22, s * 0.2), paint(shade(color, 0.7)))
        c.restore()
    return f


def book(color=(220, 90, 70)):
    def f(c, pos, ang, u):
        D = Draw(c)
        _rot(c, pos, ang)
        s = u * 0.45
        cover = poly_path([(-s * 0.1, s * 0.1), (s * 0.85, s * 0.0), (s * 0.9, s * 0.62), (-s * 0.05, s * 0.72)])
        D.shape(cover, color, line=shade(color, 0.5), lw=2.2)
        pages = poly_path([(-s * 0.02, s * 0.16), (s * 0.8, s * 0.07), (s * 0.84, s * 0.56), (s * 0.02, s * 0.65)])
        c.drawPath(pages, paint((250, 246, 232)))
        c.drawCircle(s * 0.42, s * 0.36, s * 0.14, paint((255, 200, 60)))  # подсолнух на обложке-развороте
        for k in range(10):
            a = k * 0.628
            c.drawCircle(s * 0.42 + math.cos(a) * s * 0.17, s * 0.36 + math.sin(a) * s * 0.17, s * 0.06, paint((255, 210, 70)))
        c.drawCircle(s * 0.42, s * 0.36, s * 0.08, paint((120, 80, 40)))
        c.restore()
    return f


def packet():
    def f(c, pos, ang, u):
        D = Draw(c)
        _rot(c, pos, ang)
        s = u * 0.28
        p = poly_path([(-s * 0.4, s * 0.15), (s * 0.4, s * 0.1), (s * 0.45, s * 1.0), (-s * 0.38, s * 1.05)])
        D.shape(p, (236, 214, 170), line=(150, 120, 80), lw=2)
        c.drawCircle(0, s * 0.6, s * 0.18, paint((250, 196, 60)))
        c.restore()
    return f


def seed(root=0.0):
    def f(c, pos, ang, u):
        D = Draw(c)
        _rot(c, pos, ang)
        s = u * 0.14
        sd = smooth_path(ellipse_pts(0, s * 0.9, s * 0.32, s * 0.55, 14))
        D.shape(sd, (70, 60, 56), line=(30, 26, 24), lw=1.6)
        for k in (-1, 1):
            D.stroke([(k * s * 0.12, s * 0.5), (k * s * 0.12, s * 1.3)], (230, 226, 210), 1.6)
        if root > 0:
            D.tapered([(0, s * 1.4), (s * 0.15, s * (1.4 + root * 0.7)), (-s * 0.05, s * (1.4 + root * 1.3))], s * 0.12, s * 0.03, (250, 246, 230))
        c.restore()
    return f


def cup(color=(240, 120, 100)):
    def f(c, pos, ang, u):
        D = Draw(c)
        _rot(c, pos, 1.5708)
        s = u * 0.3
        b = poly_path([(-s * 0.35, s * 0.05), (s * 0.35, s * 0.05), (s * 0.3, s * 0.75), (-s * 0.3, s * 0.75)])
        D.shape(b, color, line=shade(color, 0.5), lw=2)
        D.stroke([(s * 0.33, s * 0.2), (s * 0.6, s * 0.35), (s * 0.32, s * 0.55)], shade(color, 0.5), s * 0.08)
        c.drawOval(skia.Rect(-s * 0.33, -s * 0.02, s * 0.33, s * 0.12), paint((120, 190, 240)))
        c.restore()
    return f


def stick():
    def f(c, pos, ang, u):
        D = Draw(c)
        _rot(c, pos, ang)
        D.tapered([(0, -u * 0.6), (0, u * 0.8)], u * 0.06, u * 0.05, (150, 110, 70))
        c.restore()
    return f


def umbrella(open_=1.0, color=(240, 90, 90)):
    def f(c, pos, ang, u):
        D = Draw(c)
        c.save(); c.translate(*pos)
        D.stroke([(0, 0), (0, -u * 1.6)], (60, 50, 50), u * 0.05)
        w = u * 1.4 * open_
        top = -u * 1.6
        can = smooth_path([(-w, top + u * 0.35), (-w * 0.6, top - u * 0.15), (0, top - u * 0.32), (w * 0.6, top - u * 0.15), (w, top + u * 0.35),
                           (w * 0.5, top + u * 0.22), (0, top + u * 0.35), (-w * 0.5, top + u * 0.22)], tension=0.5)
        D.shape(can, color, line=shade(color, 0.5), lw=2.4, shadow=(-u * 0.08, -u * 0.06, shade(color, 0.78), u * 0.05))
        for k in (-0.5, 0, 0.5):
            D.stroke([(k * w, top + u * 0.3), (k * w * 0.5, top - u * 0.25)], shade(color, 0.6), 2)
        D.stroke([(0, 0), (u * 0.12, u * 0.15)], (60, 50, 50), u * 0.05)
        c.restore()
    return f


def cookie():
    def f(c, pos, ang, u):
        D = Draw(c)
        _rot(c, pos, ang)
        s = u * 0.16
        D.shape(smooth_path(ellipse_pts(0, s, s, s, 14)), (210, 150, 80), line=(140, 90, 50), lw=1.6)
        for dx, dy in ((-0.3, 0.8), (0.3, 1.2), (0.1, 0.6)):
            c.drawCircle(dx * s, dy * s, s * 0.12, paint((90, 50, 30)))
        c.restore()
    return f


def chart():
    def f(c, pos, ang, u):
        D = Draw(c)
        c.save(); c.translate(*pos)
        s = u * 0.7
        D.shape(poly_path([(-s * 0.6, -s * 0.9), (s * 0.6, -s * 0.95), (s * 0.62, s * 0.1), (-s * 0.58, s * 0.12)]), (252, 250, 240), line=(150, 140, 120), lw=2)
        for r in range(4):  # таблица: капли воды и галочки (без надписей)
            y = -s * 0.7 + r * s * 0.2
            c.drawCircle(-s * 0.35, y, s * 0.06, paint((90, 170, 230)))
            D.stroke([(s * 0.05, y), (s * 0.15, y + s * 0.07), (s * 0.35, y - s * 0.08)], (80, 170, 90), 3)
        c.restore()
    return f


def blanket_draw(c, x, y, w, h, color=(120, 160, 220)):
    D = Draw(c)
    p = smooth_path([(x, y), (x + w * 0.5, y - h * 0.15), (x + w, y), (x + w * 1.02, y + h), (x + w * 0.5, y + h * 1.08), (x - w * 0.02, y + h)], tension=0.5)
    D.shape(p, color, line=shade(color, 0.5), lw=2.4, shadow=(-10, -8, shade(color, 0.8), 6))
    for k in range(4):
        D.stroke([(x + w * (0.15 + 0.2 * k), y + h * 0.1), (x + w * (0.12 + 0.2 * k), y + h * 0.95)], (255, 255, 255), 3, alpha=0.5)


def sunflower_pot(c, x, y, stage, P, lit, wind=0.0, t=0.0, scale=1.2, sparkle=0.0, soil_hole=0.0, water=0.0, pot=True, stick=0.0, ribbon=0.0):
    """Горшок с подсолнухом. stage: 0 — только земля, 1 — росток, 2 — 4 листа, 3 — по колено,
    4 — по плечо, 5 — бутон, 6 — цветок. Непрерывные значения дают анимацию роста."""
    D = Draw(c)
    s = scale
    if not pot:
        return sunflower_ground(c, x, y, stage, P, lit, wind, t, s, sparkle, soil_hole, water, stick, ribbon)
    color = (198, 108, 72)
    body = poly_path([(x - 48 * s, y - 84 * s), (x + 48 * s, y - 84 * s), (x + 36 * s, y), (x - 36 * s, y)])
    c.drawOval(skia.Rect(x - 60 * s, y - 10 * s, x + 60 * s, y + 10 * s), paint((40, 30, 40), 0.25, blur=8))
    D.shape(body, lit(color, P), line=lit(shade(color, 0.55), P), lw=2.6, shadow=(-9 * s, -5 * s, lit(shade(color, 0.75), P), 5))
    D.stroke([(x - 40 * s, y - 50 * s), (x + 40 * s, y - 50 * s)], lit(shade(color, 0.8), P), 3)
    rim = skia.Rect(x - 56 * s, y - 100 * s, x + 56 * s, y - 80 * s)
    c.drawRoundRect(rim, 7, 7, paint(lit(shade(color, 1.08), P)))
    c.drawRoundRect(rim, 7, 7, paint(lit(shade(color, 0.55), P), style="stroke", width=2.6))
    soil = skia.Rect(x - 48 * s, y - 98 * s, x + 48 * s, y - 84 * s)
    c.drawOval(soil, paint(lit((86, 58, 42) if water < 0.5 else (60, 40, 30), P)))
    if soil_hole > 0:
        c.drawOval(skia.Rect(x - 16 * s, y - 94 * s, x + 16 * s, y - 86 * s), paint((40, 26, 20), soil_hole))
    if water > 0:
        c.drawOval(skia.Rect(x - 46 * s, y - 99 * s, x + 46 * s, y - 85 * s), paint((120, 170, 220), 0.6 * water))
        if water > 1.0:  # переливается через край
            for k in range(3):
                D.tapered([(x + (-40 + 40 * k) * s, y - 86 * s), (x + (-44 + 44 * k) * s, y - 40 * s)], 5 * s, 2 * s, (120, 180, 240), alpha=0.8)
    _plant_part(c, x, y, stage, P, lit, wind, t, s, sparkle)


def _plant_part(c, x, y, stage, P, lit, wind, t, s, sparkle):
    D = Draw(c)
    if stage <= 0.02:
        return
    top = (x, y - 92 * s)
    sway = math.sin(t * 1.7) * 0.03 + wind * (0.25 + 0.1 * math.sin(t * 7))
    h = [0, 30, 70, 200, 330, 400, 430][min(6, int(stage))] + ([0, 30, 70, 200, 330, 400, 430][min(6, int(stage) + 1)] - [0, 30, 70, 200, 330, 400, 430][min(6, int(stage))]) * (stage - int(stage)) if stage < 6 else 430
    h *= s
    tip = (top[0] + sway * h * 0.8, top[1] - h)
    midp = (top[0] + sway * h * 0.3, top[1] - h * 0.5)
    green = lit((76, 150, 70), P)
    if stage < 1.5:
        D.tapered([top, midp, tip], 5 * s, 3 * s, green)
        for k in (-1, 1):
            lf = smooth_path([tip, (tip[0] + k * 22 * s, tip[1] - 14 * s), (tip[0] + k * 34 * s, tip[1] + 2 * s), (tip[0] + k * 14 * s, tip[1] + 6 * s)], tension=0.6)
            D.shape(lf, lit((110, 190, 90), P), line=lit((50, 110, 50), P), lw=1.8)
        return
    D.tapered([top, midp, tip], 12 * s * min(1, stage / 4), 6 * s, green)
    nleaf = int(min(8, stage * 1.6))
    for i in range(nleaf):
        f = 0.25 + 0.7 * i / max(1, nleaf)
        bx = top[0] + (tip[0] - top[0]) * f
        by = top[1] + (tip[1] - top[1]) * f
        k = 1 if i % 2 else -1
        L = 60 * s * (1.1 - f * 0.5)
        lf = smooth_path([(bx, by), (bx + k * L * 0.5, by - L * 0.35 + sway * L), (bx + k * L, by - L * 0.05 + sway * L * 1.5), (bx + k * L * 0.45, by + L * 0.12)], tension=0.6)
        D.shape(lf, lit((96, 176, 80), P), line=lit((50, 110, 50), P), lw=1.8, shadow=(-4, -3, lit((70, 140, 60), P), 3))
        D.stroke([(bx, by), (bx + k * L * 0.8, by - L * 0.05 + sway * L * 1.3)], lit((60, 130, 60), P), 1.4)
    if stage >= 4.8:
        bloom = min(1.0, max(0.0, (stage - 5.0)))
        bud = 26 * s + 40 * s * bloom
        cx, cy = tip
        if bloom > 0.05:
            for ring, (n, rr, colr) in enumerate(((22, 1.55, (255, 196, 40)), (18, 1.3, (255, 214, 70)))):
                for k in range(n):
                    a = 2 * math.pi * k / n + ring * 0.12 + sway * 0.5
                    px, py = cx + math.cos(a) * bud * (0.9 + 0.35 * bloom), cy + math.sin(a) * bud * (0.9 + 0.35 * bloom) * 0.95
                    pt = smooth_path([(cx + math.cos(a) * bud * 0.8, cy + math.sin(a) * bud * 0.8),
                                      (px + math.cos(a + 1.57) * bud * 0.18, py + math.sin(a + 1.57) * bud * 0.18),
                                      (cx + math.cos(a) * bud * rr * bloom + math.cos(a) * bud * (1 - bloom), cy + math.sin(a) * bud * rr * bloom + math.sin(a) * bud * (1 - bloom)),
                                      (px - math.cos(a + 1.57) * bud * 0.18, py - math.sin(a + 1.57) * bud * 0.18)], tension=0.6)
                    D.shape(pt, lit(colr, P), line=lit((200, 130, 20), P), lw=1.4)
        D.shape(smooth_path(ellipse_pts(cx, cy, bud * 0.85, bud * 0.82, 24)), lit((110, 70, 40), P), line=lit((70, 44, 26), P), lw=2)
        rng = np.random.default_rng(2)
        for k in range(40):
            r = bud * 0.75 * math.sqrt(rng.random()); a = rng.random() * 6.28
            c.drawCircle(cx + math.cos(a) * r, cy + math.sin(a) * r, 2.2 * s, paint(lit((70, 44, 26), P)))
        if bloom < 0.05:
            for k in range(8):
                a = k * 0.785
                c.drawCircle(cx + math.cos(a) * bud * 0.8, cy + math.sin(a) * bud * 0.8, bud * 0.3, paint(lit((90, 160, 70), P)))
    if sparkle > 0:
        for k in range(10):
            a = t * 2 + k * 0.63
            px, py = x + math.cos(a * 1.3 + k) * 140 * s, y - 120 * s - abs(math.sin(a + k)) * 300 * s
            r = 3 + 3 * abs(math.sin(t * 5 + k))
            c.drawCircle(px, py, r, paint((255, 255, 230), 0.8 * sparkle))


def pigeon(c, x, y, s, face=1, flap=0.0, peck=0.0):
    D = Draw(c)
    c.save(); c.translate(x, y); c.scale(face, 1)
    body = smooth_path(ellipse_pts(0, -s * 0.5, s * 0.55, s * 0.35, 18))
    D.shape(body, (150, 156, 176), line=(80, 86, 104), lw=2)
    head = (s * 0.45 + peck * s * 0.2, -s * 0.85 + peck * s * 0.45)
    c.drawCircle(*head, s * 0.22, paint((130, 136, 160)))
    c.drawCircle(head[0] + s * 0.08, head[1] - s * 0.04, s * 0.05, paint((20, 20, 20)))
    c.drawPath(poly_path([(head[0] + s * 0.2, head[1]), (head[0] + s * 0.36, head[1] + s * 0.05), (head[0] + s * 0.2, head[1] + s * 0.08)]), paint((230, 170, 90)))
    wa = -0.3 - flap * 1.2
    wing = smooth_path([(-s * 0.1, -s * 0.6), (-s * 0.1 + math.cos(wa - 1.57) * s * 0.7, -s * 0.6 + math.sin(wa - 1.57) * s * 0.7 * (1 if flap > 0.2 else -0.3)),
                        (-s * 0.55, -s * 0.45)], tension=0.5)
    D.shape(wing, (120, 126, 150), line=(70, 76, 96), lw=2)
    D.stroke([(0, -s * 0.18), (0, 0)], (230, 120, 100), 2.5)
    c.restore()


def splash(c, x, y, t, n=14, spread=120, color=(140, 200, 255), seed=1):
    """Брызги: t — время с момента всплеска (0..0.8 с)."""
    if t < 0 or t > 0.9:
        return
    rng = np.random.default_rng(seed)
    for i in range(n):
        vx, vy = rng.uniform(-1, 1) * spread, -rng.uniform(150, 420)
        px, py = x + vx * t * 2, y + vy * t + 900 * t * t
        c.drawCircle(px, py, rng.uniform(3, 7) * (1 - t), paint(color, 0.85 * (1 - t / 0.9)))


def stream(c, x0, y0, x1, y1, t, color=(140, 200, 255)):
    """Струя воды из носика."""
    D = Draw(c)
    pts = [(x0 + (x1 - x0) * k / 8, y0 + (y1 - y0) * (k / 8) ** 2) for k in range(9)]
    D.stroke(pts, color, 7, alpha=0.75)
    for k in range(5):
        s = ((t * 3 + k / 5) % 1.0)
        px, py = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s * s
        c.drawCircle(px, py, 4, paint((220, 240, 255), 0.9))


def rain(c, t, w, h, strength=1.0, wind=0.3, seed=5):
    rng = np.random.default_rng(seed)
    n = int(260 * strength)
    xs = rng.uniform(-200, w + 200, n); ys = rng.uniform(0, h, n); sp = rng.uniform(900, 1400, n)
    for i in range(n):
        y = (ys[i] + sp[i] * t) % (h + 100) - 50
        x = xs[i] + wind * y * 0.4
        c.drawLine(x, y, x + wind * 18, y + 26, paint((200, 214, 240), 0.45, style="stroke", width=1.6))


def leaves(c, t, w, h, n=14, wind=1.0, seed=8):
    rng = np.random.default_rng(seed)
    for i in range(n):
        ph = rng.uniform(0, 10)
        x = (rng.uniform(-300, w) + wind * 500 * (t + ph)) % (w + 400) - 200
        y = rng.uniform(100, h - 100) + math.sin(t * 3 + ph) * 60
        a = t * 4 + ph
        c.save(); c.translate(x, y); c.rotate(math.degrees(a))
        c.drawOval(skia.Rect(-12, -5, 12, 5), paint((90 + int(rng.uniform(0, 60)), 150, 70), 0.9))
        c.restore()


def tears(c, x, y, t, k=1.0):
    for i in range(2):
        ph = (t * 1.3 + i * 0.5) % 1.0
        c.drawCircle(x + i * 4, y + ph * 40, 5 * k * (1 - ph * 0.5), paint((150, 210, 255), 0.85 * (1 - ph)))


def sunflower_ground(c, x, y, stage, P, lit, wind=0.0, t=0.0, s=1.0, sparkle=0.0, soil_hole=0.0, water=0.0, stick=0.0, ribbon=0.0):
    """Подсолнух в грядке: холмик земли, мокрое пятно после полива, колышек и мятная ленточка-бант."""
    D = Draw(c)
    mound = smooth_path([(x - 70 * s, y), (x - 40 * s, y - 16 * s), (x, y - 22 * s), (x + 40 * s, y - 16 * s), (x + 70 * s, y)], tension=0.5)
    D.shape(mound, lit((104, 72, 52), P), line=lit((70, 48, 36), P), lw=1.6)
    if water > 0:
        c.drawOval(skia.Rect(x - 60 * s, y - 20 * s, x + 60 * s, y - 2 * s), paint(lit((60, 40, 30), P), 0.7 * min(1, water)))
    if soil_hole > 0:
        c.drawOval(skia.Rect(x - 18 * s, y - 22 * s, x + 18 * s, y - 12 * s), paint((40, 26, 20), soil_hole))
    if stick > 0:
        D.shape(poly_path([(x + 26 * s, y - 10 * s), (x + 32 * s, y - 10 * s), (x + 32 * s, y - 300 * s * stick), (x + 26 * s, y - 300 * s * stick)]),
                lit((176, 130, 84), P), line=lit((110, 76, 50), P), lw=1.6)
    # стебель: переиспользуем рост из горшечной версии со смещённой «землёй»
    c.save(); c.translate(0, 92 * s - 18 * s)
    _sf_plant(c, x, y, stage, P, lit, wind, t, s, sparkle)
    c.restore()
    if ribbon > 0 and stage >= 2:
        by = y - 150 * s
        sway = math.sin(t * 1.7) * 0.03 + wind * (0.25 + 0.1 * math.sin(t * 7))
        bx = x + 14 * s + sway * 60 * s
        k = min(1.0, ribbon)
        mint = (120, 206, 180)
        for side in (-1, 1):
            loop = smooth_path([(bx, by), (bx + side * 26 * s * k, by - 14 * s * k), (bx + side * 30 * s * k, by + 6 * s * k)], tension=0.6)
            D.shape(loop, lit(mint, P), line=lit((60, 130, 110), P), lw=1.6)
            D.tapered([(bx, by + 2 * s), (bx + side * 12 * s, by + 26 * s * k + math.sin(t * 5 + side) * 3 * s * wind)], 6 * s, 2 * s, lit(mint, P))
        c.drawCircle(bx, by, 6 * s, paint(lit((96, 186, 160), P)))


def _sf_plant(c, x, y, stage, P, lit, wind, t, s, sparkle):
    """Растение без горшка (координаты как у sunflower_pot: земля на y - 92*s)."""
    _plant_part(c, x, y, stage, P, lit, wind, t, s, sparkle)


def magnifier(scale=1.0):
    def f(c, pos, ang, u):
        c.save(); c.translate(*pos); c.rotate(math.degrees(ang) - 90)
        s = u * 0.0042 * scale
        D = Draw(c)
        D.shape(poly_path([(-9 * s, 0), (9 * s, 0), (8 * s, 70 * s), (-8 * s, 70 * s)]), (120, 76, 50), line=(70, 44, 30), lw=2)
        c.drawCircle(0, 112 * s, 44 * s, paint((200, 230, 245), 0.55))
        c.drawCircle(0, 112 * s, 44 * s, paint((60, 60, 70), style="stroke", width=9 * s))
        D.tapered([(-22 * s, 96 * s), (-8 * s, 84 * s)], 4 * s, 2 * s, (255, 255, 255), alpha=0.8)
        c.restore()
    return f


def towel(color=(250, 214, 150)):
    def f(c, pos, ang, u):
        c.save(); c.translate(*pos); c.rotate(math.degrees(ang) - 90)
        s = u * 0.004
        D = Draw(c)
        pth = smooth_path([(-30 * s, -6 * s), (30 * s, -8 * s), (36 * s, 60 * s), (6 * s, 90 * s), (-34 * s, 70 * s)], tension=0.5)
        D.shape(pth, color, line=shade(color, 0.6), lw=2)
        for k in range(3):
            D.stroke([(-28 * s, (10 + 20 * k) * s), (30 * s, (8 + 20 * k) * s)], shade(color, 0.8), 2, alpha=0.6)
        c.restore()
    return f


def ribbon_hand():
    def f(c, pos, ang, u):
        c.save(); c.translate(*pos)
        s = u * 0.004
        D = Draw(c)
        for k, dx in enumerate((-1, 1)):
            D.tapered([(0, 0), (dx * 18 * s, 30 * s), (dx * 8 * s, 60 * s)], 7 * s, 3 * s, (120, 206, 180))
        c.restore()
    return f
