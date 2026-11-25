"""Общие детали одежды и волос для героев (рисуются в пикселях, в системе персонажа)."""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube, col


def torso_shape(J, u, sh_w, waist_w, hem_w, hem_drop, sway=0.0, flare=0.0, face=1, waist_up=0.28, chest_w=None):
    """Платье/рубашка: плечи -> талия -> подол. hem_drop — подол ниже таза (ед. головы)."""
    ch, hip = J["chest"], J["hip"]
    shn, shf = J["sh_n"], J["sh_f"]
    up = (ch - hip) / (np.linalg.norm(ch - hip) + 1e-6)
    side = np.array([-up[1], up[0]])
    cw = (chest_w or sh_w) * u
    neck_l = ch + side * (-0.12 * u) + up * (0.01 * u)
    neck_r = ch + side * (0.12 * u) + up * (0.01 * u)
    waist = hip + up * (waist_up * u)
    hem_c = hip - up * (hem_drop * u) + np.array([sway * u, 0])
    pts = [
        neck_l, shf + side * (-0.05 * u) + up * (0.01 * u), shf + side * (-0.07 * u) - up * (0.20 * u),
        waist + side * (-waist_w / 2 * u),
        hem_c + side * (-hem_w / 2 * u) + np.array([-flare * u, 0]),
        hem_c + side * (-hem_w * 0.2 * u) - up * (0.03 * u),
        hem_c + side * (hem_w * 0.2 * u) - up * (0.03 * u),
        hem_c + side * (hem_w / 2 * u) + np.array([flare * u, 0]),
        waist + side * (waist_w / 2 * u),
        shn + side * (0.07 * u) - up * (0.20 * u), shn + side * (0.05 * u) + up * (0.01 * u), neck_r,
    ]
    return smooth_path([tuple(q) for q in pts], tension=0.5), dict(neck_l=neck_l, neck_r=neck_r, hem_c=hem_c, up=up, side=side, waist=waist)


def folds(c, pts_list, color, alpha=0.5, w=2.0):
    D = Draw(c)
    for pts in pts_list:
        D.tapered(pts, w * 0.4, w * 0.4, color, alpha=alpha, mid=w)


def scarf_cap(c, R, t, fill, line, lw, pattern=None, front_drop=0.30, back_drop=0.55, scale=1.08):
    """Платок: шапочка над лбом и по затылку (рисуется поверх головы)."""
    xf = math.sin(t * 1.15) * R * 0.92
    pts = []
    xs = np.linspace(-1.5 * R, 1.5 * R, 40)
    for x in xs:
        d = (x - xf) / R
        y = -front_drop * R + 0.42 * R * d * d
        y = min(y, back_drop * R)
        pts.append((x, y))
    pts += [(1.5 * R, -2 * R), (-1.5 * R, -2 * R)]
    region = smooth_path(pts, tension=0.2)
    head = smooth_path([(math.cos(a) * R * scale * 1.0 + (t * R * 0.04 if math.sin(a) < 0 else 0), math.sin(a) * R * scale * (1.02 if math.sin(a) < 0 else 0.97))
                        for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)])
    cap = skia.Op(head, region, skia.PathOp.kIntersect_PathOp)
    if cap is None:
        return None
    D = Draw(c)
    D.shape(cap, fill, line=line, lw=lw, shadow=(-R * 0.08, -R * 0.08, shade(fill, 0.84), R * 0.08),
            light=(R * 0.06, R * 0.06, (255, 250, 235), R * 0.05))
    if pattern:
        c.save()
        c.clipPath(cap, skia.ClipOp.kIntersect, True)
        rng = np.random.default_rng(7)
        for i in range(26):
            px, py = rng.uniform(-1.3 * R, 1.3 * R), rng.uniform(-1.3 * R, 0.5 * R)
            pattern(c, px + t * R * 0.15, py, R * 0.07)
        c.restore()
    # кромка над лбом
    edge = [(x, -front_drop * R + 0.42 * R * ((x - xf) / R) ** 2) for x in np.linspace(xf - 0.85 * R, xf + 0.85 * R, 12)]
    edge = [(x, min(y, back_drop * R)) for x, y in edge]
    c.save(); c.clipPath(head, skia.ClipOp.kIntersect, True)
    D.tapered(edge, lw * 0.8, lw * 0.8, shade(fill, 0.7), mid=lw * 1.6, alpha=0.8)
    c.restore()
    return cap


def flower(c, x, y, r, petal=(255, 255, 255), center=(250, 180, 60)):
    for k in range(5):
        a = k * 2 * math.pi / 5
        c.drawCircle(x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.55, r * 0.45, paint(petal, 0.9))
    c.drawCircle(x, y, r * 0.3, paint(center))


def glasses_on_face():
    pass
