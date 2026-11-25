"""Лицо: глаза (белок, радужка с градиентом, зрачок, два блика, веки, ресницы), брови,
нос, щёки, рот с формами для фонем русской речи (интерполируются между собой).

Координаты лица: центр головы (0,0), радиус головы R, ось y вниз (как в Skia).
yaw t ∈ [-1, 1]: 0 — анфас, ±0.6 — три четверти, ±1 — почти профиль (+ вправо).
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, ellipse_pts, Draw, col, shade, mix, curve_through

# ----- формы рта: (ширина, открытие, округлость, улыбка, зубы_верх, язык, зубы_низ)
MOUTH = {
    "X":   (0.50, 0.00, 0.0, 0.00, 0.0, 0.0, 0.0),   # покой
    "MBP": (0.46, 0.00, 0.1, 0.00, 0.0, 0.0, 0.0),   # губы сомкнуты, слегка поджаты
    "A":   (0.58, 0.62, 0.2, 0.05, 0.6, 0.55, 0.15),
    "O":   (0.40, 0.55, 0.9, 0.00, 0.3, 0.3, 0.0),
    "U":   (0.28, 0.32, 1.0, 0.00, 0.0, 0.1, 0.0),
    "I":   (0.66, 0.26, 0.0, 0.25, 0.9, 0.2, 0.5),
    "E":   (0.62, 0.40, 0.1, 0.15, 0.8, 0.4, 0.3),
    "Y":   (0.56, 0.30, 0.1, 0.05, 0.7, 0.3, 0.2),
    "FV":  (0.52, 0.12, 0.0, 0.05, 1.0, 0.0, 0.0),
    "S":   (0.60, 0.14, 0.0, 0.10, 1.0, 0.0, 0.8),
    "SH":  (0.40, 0.26, 0.7, 0.00, 0.9, 0.0, 0.6),
    "T":   (0.54, 0.28, 0.1, 0.05, 0.6, 0.85, 0.2),
    "K":   (0.52, 0.36, 0.2, 0.00, 0.5, 0.3, 0.2),
    "R":   (0.50, 0.30, 0.3, 0.00, 0.6, 0.7, 0.2),
    "SMILE_OPEN": (0.70, 0.42, 0.1, 0.55, 0.9, 0.5, 0.0),
    "GASP": (0.42, 0.62, 0.8, 0.00, 0.3, 0.3, 0.0),
    "CRY": (0.62, 0.36, 0.2, -0.45, 0.6, 0.2, 0.3),
}


def mouth_vec(weights):
    """weights: {viseme: w} -> средневзвешенный вектор параметров."""
    tot = sum(weights.values()) or 1.0
    v = np.zeros(7)
    for k, w in weights.items():
        v += np.array(MOUTH[k]) * w
    return v / tot


class FaceStyle:
    def __init__(self, skin, line, iris, iris2, lash, brow, blush, lip, female=True, eye_size=1.0, eye_sep=0.36,
                 eye_y=0.05, mouth_y=0.52, nose_y=0.30, brow_th=1.0, glasses=None, wrinkles=False, lashes=3, eye_shape=1.0):
        self.__dict__.update(locals())
        del self.__dict__["self"]


def feat_x(theta, t, R, k=0.92):
    a = theta + t * 1.15
    return math.sin(a) * R * k, math.cos(a)


def draw_eye(c, x, y, rx, ry, fs, look, blink, squint, wide, lid_down, side, t):
    """Один глаз. look=(lx,ly) -1..1; blink 0..1; squint — нижнее веко (улыбка)."""
    D = Draw(c)
    ry_eff = ry * (1 + 0.12 * wide)
    eye = smooth_path(ellipse_pts(x, y, rx, ry_eff, 28))
    # белок
    c.save()
    c.clipPath(eye, skia.ClipOp.kIntersect, True)
    c.drawPath(eye, paint((250, 248, 244)))
    # радужка
    ix = x + look[0] * rx * 0.42
    iy = y + look[1] * ry_eff * 0.30 + ry_eff * 0.06
    ir = min(rx, ry_eff) * 0.78
    shader = skia.GradientShader.MakeLinear([skia.Point(ix, iy - ir), skia.Point(ix, iy + ir)],
                                            [col(shade(fs.iris, 0.55)), col(fs.iris), col(fs.iris2)], [0.0, 0.5, 1.0])
    p = skia.Paint(AntiAlias=True); p.setShader(shader)
    c.drawOval(skia.Rect(ix - ir * 0.92, iy - ir, ix + ir * 0.92, iy + ir), p)
    c.drawOval(skia.Rect(ix - ir * 0.5, iy - ir * 0.55, ix + ir * 0.5, iy + ir * 0.55), paint((22, 14, 18)))
    # тень верхнего века на белке
    c.drawOval(skia.Rect(x - rx * 1.3, y - ry_eff * 2.05, x + rx * 1.3, y - ry_eff * 0.55), paint((120, 90, 110), 0.22, blur=ry * 0.25))
    # блики
    c.drawOval(skia.Rect(ix - ir * 0.62, iy - ir * 0.72, ix - ir * 0.12, iy - ir * 0.22), paint((255, 255, 255)))
    c.drawOval(skia.Rect(ix + ir * 0.25, iy + ir * 0.25, ix + ir * 0.48, iy + ir * 0.48), paint((255, 255, 255), 0.85))
    c.restore()
    # веко (моргание / прищур сверху)
    close = max(blink, lid_down)
    if close > 0.02:
        top = y - ry_eff - 2
        bot = y - ry_eff + 2 * ry_eff * close + 1
        lid = skia.Path()
        lid.addRect(skia.Rect(x - rx * 1.4, top - ry, x + rx * 1.4, bot))
        lid = skia.Op(lid, eye, skia.PathOp.kIntersect_PathOp)
        if lid is not None:
            c.drawPath(lid, paint(fs.skin))
            c.drawPath(lid, paint(shade(fs.skin, 0.82), 0.5, blur=2))
    if squint > 0.02:
        bot = y + ry_eff + 2
        topq = y + ry_eff - 2 * ry_eff * squint * 0.6
        lid = skia.Path()
        cx_ = x
        lid.moveTo(x - rx * 1.4, bot + ry); lid.lineTo(x - rx * 1.4, topq + ry_eff * 0.3)
        lid.quadTo(cx_, topq - ry_eff * 0.25, x + rx * 1.4, topq + ry_eff * 0.3); lid.lineTo(x + rx * 1.4, bot + ry); lid.close()
        lid = skia.Op(lid, eye, skia.PathOp.kIntersect_PathOp)
        if lid is not None:
            c.drawPath(lid, paint(fs.skin))
    # контур верхнего века + ресницы
    lid_y = y - ry_eff + 2 * ry_eff * close
    if close > 0.92:  # закрытый глаз — дуга
        D.tapered([(x - rx * 1.05, y + ry * 0.1), (x, y + ry * 0.35), (x + rx * 1.05, y + ry * 0.1)], 2, 2, fs.lash, mid=4.5)
    else:
        pts = []
        for i in range(9):
            a = math.pi + math.pi * i / 8
            px_ = x + rx * 1.04 * math.cos(a)
            py_ = y + ry_eff * 1.02 * math.sin(a)
            py_ = max(py_, lid_y) if close > 0.02 else py_
            pts.append((px_, py_))
        D.tapered(pts, 1.6, 2.4, fs.lash, mid=4.6 * (1.0 if fs.female else 0.8))
        if fs.lashes:
            outer = 1 if side > 0 else -1
            for k in range(fs.lashes):
                bx = x + outer * rx * (0.72 + 0.14 * k)
                by = max(y - ry_eff * (0.72 - 0.25 * k), lid_y)
                D.tapered([(bx, by), (bx + outer * rx * 0.28, by - ry * 0.26)], 2.2, 0.6, fs.lash)
        # нижнее веко — лёгкий штрих
        D.tapered([(x - rx * 0.6, y + ry_eff * 0.95), (x, y + ry_eff * 1.02), (x + rx * 0.55, y + ry_eff * 0.95)], 0.6, 0.6,
                  shade(fs.skin, 0.72), mid=1.4, alpha=0.7)


def draw_brow(c, x, y, w, fs, up, inner, angle_side, t, side):
    D = Draw(c)
    yy = y - up * w * 0.35
    inner_dx = -side  # к центру лица
    xi = x + inner_dx * w * 0.5
    xo = x - inner_dx * w * 0.5
    yi = yy - inner * w * 0.28
    yo = yy + inner * w * 0.08
    mid = (x, yy - w * 0.12 - max(0, -inner) * 0 + 0)
    D.tapered([(xi, yi), mid, (xo, yo + w * 0.05)], 3.2 * fs.brow_th, 1.6 * fs.brow_th, fs.brow, mid=4.6 * fs.brow_th)


def draw_mouth(c, x, y, scale, vec, fs, t):
    """Рот. vec = (ширина, открытие, округлость, улыбка, зубы_верх, язык, зубы_низ)."""
    D = Draw(c)
    w, o, rnd, sm, tu, tg, tl = vec
    w = w * scale * (1 - 0.35 * abs(t))
    hw = w / 2
    oh = o * scale * 0.55
    sm_px = sm * scale * 0.18
    if oh < 1.2:  # закрытый рот — линия с изгибом улыбки
        pts = [(x - hw, y - sm_px), (x - hw * 0.4, y + sm_px * 0.15), (x + hw * 0.4, y + sm_px * 0.15), (x + hw, y - sm_px)]
        D.tapered(pts, 1.6, 1.6, shade(fs.lip, 0.55), mid=3.0)
        D.tapered([(x - hw * 0.35, y + scale * 0.09 + sm_px * 0.2), (x + hw * 0.35, y + scale * 0.09 + sm_px * 0.2)], 1.0, 1.0, shade(fs.skin, 0.8), alpha=0.6, mid=2.0)
        return
    # открытый рот: верхняя губа с изгибом улыбки, нижняя — дуга
    k = rnd
    top_mid = y - oh * (0.30 + 0.25 * k) + sm_px * 0.3
    bot_mid = y + oh * (0.75 + 0.15 * k) + sm_px * 0.2
    corner_y = y - sm_px
    hwk = hw * (1 - 0.15 * k)
    pts = [(x - hwk, corner_y), (x - hwk * 0.55, top_mid + oh * 0.05), (x, top_mid), (x + hwk * 0.55, top_mid + oh * 0.05),
           (x + hwk, corner_y), (x + hwk * 0.6, bot_mid - oh * 0.15 * (1 - k)), (x, bot_mid), (x - hwk * 0.6, bot_mid - oh * 0.15 * (1 - k))]
    path = smooth_path(pts, tension=0.55)
    c.drawPath(path, paint((92, 30, 42)))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    if tg > 0.02:
        c.drawOval(skia.Rect(x - hwk * 0.75, bot_mid - oh * 0.55 * tg, x + hwk * 0.75, bot_mid + oh * 0.6), paint((226, 110, 118)))
    if tu > 0.02:
        c.drawRect(skia.Rect(x - hwk, top_mid - 4, x + hwk, top_mid + oh * 0.28 * tu + 1), paint((252, 250, 246)))
    if tl > 0.02:
        c.drawRect(skia.Rect(x - hwk, bot_mid - oh * 0.22 * tl, x + hwk, bot_mid + 4), paint((246, 244, 238)))
    c.restore()
    c.drawPath(path, paint(shade(fs.lip, 0.5), style="stroke", width=2.2))
    # нижняя губа — мягкий блик
    D.tapered([(x - hwk * 0.4, bot_mid + scale * 0.06), (x + hwk * 0.4, bot_mid + scale * 0.06)], 1.0, 1.0, shade(fs.skin, 0.8), alpha=0.5, mid=2.4)


def draw_face(c, R, fs, st, t, pitch=0.0):
    """st: dict — look(lx,ly), blink, squint, wide, lid, brow_up, brow_inner, brow_asym, mouth (вектор), smile_cheek."""
    D = Draw(c)
    py = pitch * R * 0.18
    ey = R * fs.eye_y + py
    rx = R * 0.20 * fs.eye_size * fs.eye_shape
    ry = R * 0.25 * fs.eye_size
    # щёки
    for s in (-1, 1):
        cx_, vis = feat_x(s * 0.62, t, R, 0.9)
        if vis > 0.05:
            c.drawOval(skia.Rect(cx_ - R * 0.16 * vis, R * 0.33 + py - R * 0.09, cx_ + R * 0.16 * vis, R * 0.33 + py + R * 0.09),
                       paint(fs.blush, 0.38 + 0.25 * st.get("blush", 0), blur=R * 0.07))
    # глаза (дальний рисуем первым)
    order = sorted((-1, 1), key=lambda s: feat_x(s * fs.eye_sep, t, R)[1])
    for s in order:
        ex, vis = feat_x(s * fs.eye_sep, t, R)
        if vis < 0.12:
            continue
        sq = st.get("squint", 0)
        draw_eye(c, ex, ey, rx * (0.35 + 0.65 * vis), ry, fs, st.get("look", (0, 0)), st.get("blink", 0), sq,
                 st.get("wide", 0), st.get("lid", 0), s, t)
        bu = st.get("brow_up", 0) + (st.get("brow_asym", 0) if s > 0 else 0)
        draw_brow(c, ex, ey - ry * 1.55 - R * 0.02, rx * 2.0 * (0.4 + 0.6 * vis), fs, bu, st.get("brow_inner", 0), 0, t, s)
        if fs.glasses:
            g = fs.glasses
            gr = rx * 1.55 * (0.4 + 0.6 * vis)
            c.drawOval(skia.Rect(ex - gr, ey - ry * 1.25, ex + gr, ey + ry * 1.25), paint(g, style="stroke", width=2.6))
            c.drawOval(skia.Rect(ex - gr, ey - ry * 1.25, ex + gr, ey + ry * 1.25), paint((255, 255, 255), 0.10))
        if fs.wrinkles:
            ox = ex + s * rx * 1.25
            D.tapered([(ox, ey + ry * 0.2), (ox + s * rx * 0.35, ey + ry * 0.45)], 1, 1, shade(fs.skin, 0.75), alpha=0.6, mid=1.6)
    if fs.glasses:
        lx, _ = feat_x(-fs.eye_sep, t, R); rx2, _ = feat_x(fs.eye_sep, t, R)
        D.stroke([(lx + rx * 1.2, ey - ry * 0.4), ((lx + rx2) / 2, ey - ry * 0.65), (rx2 - rx * 1.2, ey - ry * 0.4)], fs.glasses, 2.4)
    # нос
    nx, _ = feat_x(0, t, R, 0.98)
    ny = R * fs.nose_y + py
    D.tapered([(nx - R * 0.05 * (1 if t >= 0 else -1) * 0.4, ny - R * 0.06), (nx + R * 0.04 * t, ny + R * 0.03),
               (nx + R * 0.07 * (1 - abs(t)) - R * 0.05, ny + R * 0.05)], 1.2, 1.2, shade(fs.skin, 0.66), mid=2.6)
    c.drawOval(skia.Rect(nx - R * 0.035, ny - R * 0.05, nx + R * 0.005, ny - R * 0.02), paint((255, 255, 255), 0.45))
    # рот
    mx, _ = feat_x(0, t, R, 0.9)
    draw_mouth(c, mx, R * fs.mouth_y + py, R, st.get("mouth", mouth_vec({"X": 1})), fs, t)
