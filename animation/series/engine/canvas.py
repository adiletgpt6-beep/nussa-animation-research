"""Векторная 2D-графика на Skia: гладкие формы по точкам, сужающиеся штрихи, мягкие тени, градиенты.

Все размеры — в пикселях кадра 1920×1080. Цвета — '#rrggbb' или (r, g, b[, a]) 0–255.
"""
import math
import numpy as np
import skia

W, H = 1920, 1080


def col(c, a=None):
    if isinstance(c, str):
        c = c.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        al = 255 if a is None else int(a * 255) if a <= 1 else int(a)
        return skia.Color(r, g, b, al)
    if len(c) == 3:
        al = 255 if a is None else int(a * 255) if a <= 1 else int(a)
        return skia.Color(int(c[0]), int(c[1]), int(c[2]), al)
    return skia.Color(*[int(x) for x in c])


def mix(c1, c2, t):
    a, b = rgb(c1), rgb(c2)
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    return tuple(c[:3])


def shade(c, k):
    """k<1 темнее (с лёгким сдвигом в холодное), k>1 светлее."""
    r, g, b = rgb(c)
    if k < 1:
        return (r * k * 0.97, g * k * 0.98, min(255, b * k * 1.06 + 6))
    return tuple(min(255, x + (255 - x) * (k - 1)) for x in (r, g, b))


def paint(color, alpha=None, aa=True, style="fill", width=1.0, blur=0.0, cap="round"):
    p = skia.Paint(AntiAlias=aa, Color=col(color, alpha))
    if style == "stroke":
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(width)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def smooth_path(pts, closed=True, tension=0.5):
    """Catmull-Rom -> кубические Безье. pts: [(x, y), ...]."""
    p = skia.Path()
    n = len(pts)
    if n < 2:
        return p
    P = [np.array(q, float) for q in pts]
    p.moveTo(*P[0])
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[i]
        p1, p2 = P[i], P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else P[(i + 1) % n]
        c1 = p1 + (p2 - p0) * tension / 3
        c2 = p2 - (p3 - p1) * tension / 3
        p.cubicTo(*c1, *c2, *p2)
    if closed:
        p.close()
    return p


def poly_path(pts, closed=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p


def ellipse_pts(cx, cy, rx, ry, n=24, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def resample(pts, n):
    P = np.array(pts, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if d[-1] < 1e-6:
        return np.repeat(P[:1], n, axis=0)
    t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, P[:, 0]), np.interp(t, d, P[:, 1])]


def curve_through(pts, n=24):
    """Гладкая кривая через точки (Catmull-Rom), возвращает массив n точек."""
    P = [np.array(q, float) for q in pts]
    if len(P) == 2:
        return np.linspace(P[0], P[1], n)
    out = []
    segs = len(P) - 1
    per = max(2, n // segs)
    for i in range(segs):
        p0 = P[max(0, i - 1)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(len(P) - 1, i + 2)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return np.array(out)


def tube(pts, widths, n=28):
    """Контур «трубки» вдоль кривой (конечности): widths — ширины в узлах (интерполируются)."""
    C = curve_through(pts, n)
    w = np.interp(np.linspace(0, 1, len(C)), np.linspace(0, 1, len(widths)), widths)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    N = np.c_[-T[:, 1], T[:, 0]]
    L = C + N * w[:, None] / 2
    R = C - N * w[:, None] / 2
    # скруглённые концы
    def cap(center, dirv, r, steps=6):
        a0 = math.atan2(dirv[1], dirv[0])
        return [(center[0] + r * math.cos(a0 + math.pi / 2 - math.pi * k / steps),
                 center[1] + r * math.sin(a0 + math.pi / 2 - math.pi * k / steps)) for k in range(steps + 1)]
    end = cap(C[-1], T[-1], w[-1] / 2)
    start = cap(C[0], -T[0], w[0] / 2)
    outline = list(map(tuple, L)) + end[1:-1] + list(map(tuple, R[::-1])) + start[1:-1]
    return poly_path(outline), C


class Draw:
    """Обёртка над холстом: заливка + контур + мягкая тень внутри формы + блик."""

    def __init__(self, canvas):
        self.c = canvas

    def shape(self, path, fill, line=None, lw=3.0, shadow=None, light=None, alpha=None):
        c = self.c
        c.drawPath(path, paint(fill, alpha))
        if shadow is not None:  # (смещение dx, dy, цвет, мягкость)
            dx, dy, sc, soft = shadow
            c.save()
            c.clipPath(path, skia.ClipOp.kIntersect, True)
            inv = skia.Path(path)
            inv.offset(dx, dy)
            sh = skia.Path()
            sh.addRect(skia.Rect(-4000, -4000, 8000, 8000))
            sh = skia.Op(sh, inv, skia.PathOp.kDifference_PathOp) or sh
            c.drawPath(sh, paint(sc, 1.0 if alpha is None else alpha, blur=soft))
            c.restore()
        if light is not None:  # (dx, dy, цвет, мягкость) — подсветка с края
            dx, dy, lc, soft = light
            c.save()
            c.clipPath(path, skia.ClipOp.kIntersect, True)
            inv = skia.Path(path)
            inv.offset(dx, dy)
            lp = skia.Op(path, inv, skia.PathOp.kDifference_PathOp)
            if lp is not None:
                c.drawPath(lp, paint(lc, 0.55 if alpha is None else alpha * 0.55, blur=soft))
            c.restore()
        if line is not None and lw > 0:
            c.drawPath(path, paint(line, alpha, style="stroke", width=lw))

    def stroke(self, pts, color, w=3.0, alpha=None, smooth=True):
        p = smooth_path(pts, closed=False) if smooth else poly_path(pts, closed=False)
        self.c.drawPath(p, paint(color, alpha, style="stroke", width=w))

    def tapered(self, pts, w0, w1, color, alpha=None, mid=None):
        """Сужающийся штрих (брови, ресницы, складки)."""
        widths = [w0, mid if mid is not None else (w0 + w1) / 2, w1]
        path, _ = tube(pts, widths, n=18)
        self.c.drawPath(path, paint(color, alpha))

    def ellipse(self, cx, cy, rx, ry, fill, line=None, lw=2.0, rot=0.0, alpha=None, blur=0.0):
        p = smooth_path(ellipse_pts(cx, cy, rx, ry, 20, rot))
        self.c.drawPath(p, paint(fill, alpha, blur=blur))
        if line is not None:
            self.c.drawPath(p, paint(line, alpha, style="stroke", width=lw))
        return p

    def soft_shadow(self, cx, cy, rx, ry, alpha=0.25, color=(40, 30, 50), blur=12):
        self.c.drawOval(skia.Rect(cx - rx, cy - ry, cx + rx, cy + ry), paint(color, alpha, blur=blur))


def gradient_rect(canvas, rect, stops, vertical=True):
    x0, y0, x1, y1 = rect
    pts = [skia.Point(x0, y0), skia.Point(x0, y1) if vertical else skia.Point(x1, y0)]
    colors = [col(c) for c, _ in stops]
    pos = [p for _, p in stops]
    shader = skia.GradientShader.MakeLinear(pts, colors, pos)
    p = skia.Paint(AntiAlias=True)
    p.setShader(shader)
    canvas.drawRect(skia.Rect(x0, y0, x1, y1), p)


def radial(canvas, cx, cy, r, stops, alpha=1.0):
    colors = [col(c, a) for c, a, _ in stops]
    pos = [p for _, _, p in stops]
    shader = skia.GradientShader.MakeRadial(skia.Point(cx, cy), r, colors, pos)
    p = skia.Paint(AntiAlias=True, Alphaf=alpha)
    p.setShader(shader)
    canvas.drawCircle(cx, cy, r, p)


def noise_image(w, h, seed=1, scale=1.0, strength=10):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h // 2 + 1, w // 2 + 1)).astype(np.float32)
    import cv2
    n = cv2.GaussianBlur(n, (0, 0), 1.0 * scale)
    n = cv2.resize(n, (w, h))
    n = (n - n.min()) / (n.max() - n.min())
    a = np.zeros((h, w, 4), np.uint8)
    v = (n * 255).astype(np.uint8)
    a[..., 0] = v; a[..., 1] = v; a[..., 2] = v; a[..., 3] = strength
    return skia.Image.fromarray(a, colorType=skia.ColorType.kRGBA_8888_ColorType)
