"""Ёжик Колючкин — безмолвный комический персонаж. Любопытный, обидчивый, сворачивается в клубок,
шевелит носом, фыркает. Рисуется отдельно от человеческого рига."""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube

BODY = (132, 96, 70)
SPIKE = (96, 66, 48)
FACE = (236, 206, 170)


def draw(c, x, y, s, face=1, sniff=0.0, ball=0.0, blink=0.0, step=0.0, look=0.0, sy=1.0, wet=0.0):
    """x,y — точка на земле; s — размер (px); ball 0..1 — свернуться клубком; step — фаза шага."""
    D = Draw(c)
    c.save()
    c.translate(x, y)
    c.scale(face, sy)
    c.drawOval(skia.Rect(-s * 0.55, -s * 0.06, s * 0.55, s * 0.06), paint((40, 30, 40), 0.22, blur=s * 0.05))
    # лапки
    if ball < 0.6:
        for k, ph in enumerate((0, math.pi)):
            lx = (-0.22 + 0.4 * k) * s + math.sin(step + ph) * s * 0.06
            ly = -abs(math.cos(step + ph)) * s * 0.04
            c.drawOval(skia.Rect(lx - s * 0.07, ly - s * 0.08, lx + s * 0.07, ly + s * 0.01), paint(shade(FACE, 0.8)))
    by = -s * (0.36 - 0.06 * ball)
    rx, ry = s * (0.48 - 0.06 * ball), s * (0.32 + 0.06 * ball)
    # иглы
    rng = np.random.default_rng(5)
    for i in range(42):
        a = math.pi * (0.95 + 1.15 * i / 41) + (math.pi * 0.5 * ball if i % 2 else 0)
        L = s * (0.16 + 0.05 * rng.random())
        bx, by_ = rx * 0.85 * math.cos(a), by + ry * 0.85 * math.sin(a)
        tx, ty = bx + math.cos(a + 0.35) * L * 1.2, by_ + math.sin(a + 0.35) * L * 1.2
        D.tapered([(bx, by_), (tx, ty)], s * 0.07, s * 0.01, SPIKE if i % 3 else shade(SPIKE, 1.25))
    body = smooth_path(ellipse_pts(0, by, rx, ry, 24))
    D.shape(body, BODY, line=shade(BODY, 0.55), lw=2.2, shadow=(-s * 0.05, -s * 0.05, shade(BODY, 0.8), s * 0.05))
    if ball < 0.85:
        # мордочка
        fx = rx * 0.55
        muzzle = smooth_path([(fx - s * 0.18, by - s * 0.12), (fx + s * 0.18, by - s * 0.02), (fx + s * 0.34 + sniff * s * 0.03, by + s * 0.06),
                              (fx + s * 0.12, by + s * 0.20), (fx - s * 0.16, by + s * 0.20)], tension=0.6)
        D.shape(muzzle, FACE, line=shade(FACE, 0.6), lw=2.0)
        nx, ny = fx + s * 0.34 + sniff * s * 0.03, by + s * 0.06 + math.sin(sniff * 6) * s * 0.01
        c.drawCircle(nx, ny, s * 0.05, paint((30, 20, 20)))
        c.drawCircle(nx - s * 0.015, ny - s * 0.015, s * 0.015, paint((255, 255, 255), 0.8))
        ex, ey = fx + s * 0.04 + look * s * 0.02, by - s * 0.02
        if blink > 0.5:
            D.tapered([(ex - s * 0.04, ey), (ex + s * 0.04, ey)], 2, 2, (30, 20, 20), mid=3)
        else:
            c.drawCircle(ex, ey, s * 0.045, paint((30, 20, 20)))
            c.drawCircle(ex - s * 0.012, ey - s * 0.015, s * 0.016, paint((255, 255, 255)))
        c.drawCircle(fx - s * 0.05, by + s * 0.08, s * 0.04, paint((250, 140, 130), 0.45, blur=s * 0.02))
        # ухо
        c.drawOval(skia.Rect(fx - s * 0.16, by - s * 0.17, fx - s * 0.06, by - s * 0.07), paint(shade(FACE, 0.85)))
    if wet > 0:
        for k in range(3):
            c.drawCircle(-s * 0.2 + k * s * 0.2, by - ry - s * 0.05 * k, s * 0.03, paint((120, 180, 255), wet))
    c.restore()
