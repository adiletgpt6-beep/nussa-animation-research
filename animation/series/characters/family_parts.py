"""Общие детали семьи: хиджаб с открытым овалом лица, платочек с косичками, волосы,
вид со спины (без лица). Координаты — система головы: центр (0,0), радиус R, y вниз.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube


def feat_center(t, R):
    return math.sin(t * 1.15) * R * 0.92


def hijab_outer(R, t, p, drape=2.05, width=0.95):
    """Силуэт хиджаба: макушка, бока, мягкий спуск на плечи и грудь."""
    xf = feat_center(t, R)
    sw = p.get("scarf_sway", 0.0)
    w = width
    pts = []
    for a in np.linspace(math.pi * 0.90, math.pi * 2.10, 24):
        pts.append((math.cos(a) * R * 1.12 * w + xf * 0.07, math.sin(a) * R * 1.10 - R * 0.05))
    pts += [(R * 1.22 * w + xf * 0.08, R * 0.80), (R * 1.52 * w + sw * R * 0.12, R * 1.62), (R * 1.25 * w, drape * R),
            (xf * 0.45 + sw * R * 0.1, drape * R + R * 0.16), (-R * 1.25 * w, drape * R),
            (-R * 1.52 * w + sw * R * 0.12, R * 1.62), (-R * 1.22 * w + xf * 0.08, R * 0.80)]
    return smooth_path(pts, tension=0.5)


def face_opening(R, t, top=-0.62, bot=1.30, w=0.95):
    xf = feat_center(t, R)
    cy = (top + bot) / 2 * R
    ry = (bot - top) / 2 * R
    rx = w * R * (1 - 0.20 * abs(t))
    pts = ellipse_pts(xf * 0.86, cy, rx, ry, 36)
    # чуть заострённый низ, мягкая «капля» под подбородком
    pts = [(x, y + max(0, (y - cy) / ry) ** 3 * R * 0.10) for x, y in pts]
    return smooth_path(pts, tension=0.5)


def hijab_back(c, R, t, p, lw, fill, line):
    """Задний слой: заполняет силуэт (под подбородком — затенённая ткань)."""
    D = Draw(c)
    outer = hijab_outer(R, t, p)
    D.shape(outer, shade(fill, 0.80), line=line, lw=lw)


def hijab_front(c, R, t, p, lw, fill, line, skin, pattern=None, back=False):
    D = Draw(c)
    outer = hijab_outer(R, t, p)
    if back:
        frame = outer
    else:
        frame = skia.Op(outer, face_opening(R, t), skia.PathOp.kDifference_PathOp) or outer
    D.shape(frame, fill, line=line, lw=lw, shadow=(-R * 0.10 * p.get("face", 1), -R * 0.07, shade(fill, 0.84), R * 0.10),
            light=(R * 0.07 * p.get("face", 1), R * 0.07, (255, 246, 240), R * 0.06))
    xf = feat_center(t, R)
    c.save()
    c.clipPath(frame, skia.ClipOp.kIntersect, True)
    if pattern:
        pattern(c, R, t)
    # складки ткани на спуске
    for k, (x0, x1) in enumerate(((-0.95, -1.10), (0.95, 1.12), (-0.45, -0.55), (0.55, 0.62))):
        D.tapered([(x0 * R + xf * 0.1, R * 1.05), ((x0 + x1) / 2 * R, R * 1.6), (x1 * R, R * 2.15)], R * 0.015, R * 0.01,
                  shade(fill, 0.70), alpha=0.55, mid=R * 0.05)
    if back:
        D.tapered([(-R * 0.3, -R * 0.6), (0, R * 0.2), (R * 0.15, R * 1.2)], R * 0.01, R * 0.01, shade(fill, 0.72), alpha=0.5, mid=R * 0.05)
    c.restore()
    if not back:
        # мягкая тень от ткани на лице
        op = face_opening(R, t)
        c.save(); c.clipPath(op, skia.ClipOp.kIntersect, True)
        c.drawPath(op, paint(shade(skin, 0.72), 0.35, style="stroke", width=R * 0.16, blur=R * 0.05))
        c.restore()
        # кромка-подворот вокруг лица
        c.drawPath(op, paint(shade(fill, 1.06), 0.9, style="stroke", width=R * 0.06))
        c.drawPath(op, paint(line, 0.9, style="stroke", width=lw * 0.9))


def hair_mass(c, R, t, lw, color, fringe_drop=0.34, clumps=7, side_len=0.35, seed=3, volume=1.08):
    """Растрёпанные волосы: шапка с прядями чёлки и объёмом на макушке."""
    xf = feat_center(t, R)
    D = Draw(c)
    rng = np.random.default_rng(seed)
    pts = []
    xs = np.linspace(-1.5 * R, 1.5 * R, 80)
    jit = rng.uniform(0.6, 1.0, clumps + 2)
    for x in xs:
        d = (x - xf) / R
        base = -fringe_drop * R + 0.40 * R * d * d
        if abs(d) < 1.0:
            ph = (d + 1.0) / 2.0 * clumps
            i = int(ph)
            base += R * 0.16 * jit[i] * (abs((ph % 1.0) - 0.5) * 2) ** 1.4
        lim = side_len * R if (x - xf) * (1 if t >= 0 else -1) > 0 else 0.55 * R
        pts.append((x, min(base, lim)))
    pts += [(1.5 * R, -2 * R), (-1.5 * R, -2 * R)]
    region = smooth_path(pts, tension=0.15)
    blob = []
    for k, a in enumerate(np.linspace(0, 2 * math.pi, 48, endpoint=False)):
        bump = 1.0 + (0.045 * math.sin(a * 7 + seed) if math.sin(a) < 0 else 0)
        blob.append((math.cos(a) * R * volume * bump - t * R * 0.05, math.sin(a) * R * (volume + 0.03 if math.sin(a) < 0 else 0.98) * bump))
    head = smooth_path(blob, tension=0.5)
    cap = skia.Op(head, region, skia.PathOp.kIntersect_PathOp)
    if cap is None:
        return None
    D.shape(cap, color, line=shade(color, 0.55), lw=lw, shadow=(-R * 0.08, -R * 0.07, shade(color, 0.72), R * 0.07))
    c.save(); c.clipPath(cap, skia.ClipOp.kIntersect, True)
    # пряди и блик
    for k in range(6):
        x0 = xf + (k - 2.5) * R * 0.28
        D.tapered([(x0 - R * 0.1, -R * 0.95), (x0, -R * 0.62), (x0 + R * 0.06, -R * 0.36)], R * 0.01, R * 0.01, shade(color, 0.66), alpha=0.6, mid=R * 0.03)
    D.tapered([(xf - R * 0.65, -R * 0.70), (xf - R * 0.15, -R * 0.93), (xf + R * 0.35, -R * 0.80)], R * 0.02, R * 0.02,
              shade(color, 1.9), mid=R * 0.07, alpha=0.55)
    c.restore()
    return cap


def hair_back_full(c, R, lw, color, nape=0.45):
    """Вид со спины: волосы покрывают голову, видна шея-затылок снизу."""
    D = Draw(c)
    blob = [(math.cos(a) * R * 1.08, math.sin(a) * R * (1.08 if math.sin(a) < 0 else 1.0) * (1 if math.sin(a) < 0 else nape + 0.5))
            for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    path = smooth_path(blob)
    D.shape(path, color, line=shade(color, 0.55), lw=lw, shadow=(-R * 0.08, -R * 0.08, shade(color, 0.7), R * 0.08))
    c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
    for k in range(7):
        x0 = (k - 3) * R * 0.28
        D.tapered([(x0 * 0.6, -R * 0.9), (x0, -R * 0.2), (x0 * 1.1, R * 0.5)], R * 0.01, R * 0.01, shade(color, 0.68), alpha=0.55, mid=R * 0.03)
    c.restore()
