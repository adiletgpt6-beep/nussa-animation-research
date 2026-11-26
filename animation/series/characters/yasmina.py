"""Ясмина (Ясми), 5–6 лет — младшая сестра. Весёлая, искренняя, очень эмоциональная, задаёт много вопросов,
иногда удивляет брата находчивостью. Двигается живо: подпрыгивает, кружится, всплёскивает руками.

Силуэт: солнечно-жёлтый платочек в белый горошек, завязанный сзади узелком; из-под него — чёлка и
две косички с мятными бантиками; персиковое платье с белым воротничком и кармашком-цветком;
сиреневые легинсы, мятные кеды.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube
from character import Design
from face import FaceStyle
from common_parts import torso_shape, folds, scarf_cap, flower
from family_parts import feat_center, hair_back_full

SKIN = (247, 212, 188)
HAIR = (86, 54, 42)
SCARF = (255, 208, 96)
DRESS = (246, 162, 140)
BOW = (120, 206, 180)


def draw_torso(c, J, p, lw):
    u = p["u"]
    f = p.get("face", 1)
    D = Draw(c)
    sway = p.get("sway", 0.0)
    path, ref = torso_shape(J, u, 0.58, 0.50, 1.06, 0.42, sway=sway * 0.28, flare=abs(sway) * 0.06, waist_up=0.30)
    D.shape(path, DRESS, line=shade(DRESS, 0.56), lw=lw, shadow=(-0.10 * u * f, -0.06 * u, shade(DRESS, 0.84), 0.05 * u),
            light=(0.06 * u * f, 0.05 * u, (255, 236, 226), 0.04 * u))
    up, side, waist, hem = ref["up"], ref["side"], ref["waist"], ref["hem_c"]
    ch = J["chest"]
    if not p.get("back"):
        for sgn in (-1, 1):
            cl = smooth_path([tuple(ch + up * 0.01 * u), tuple(ch + side * (sgn * 0.17 * u) - up * 0.02 * u),
                              tuple(ch + side * (sgn * 0.13 * u) - up * 0.11 * u), tuple(ch - up * 0.07 * u)], tension=0.5)
            D.shape(cl, (255, 252, 246), line=shade(DRESS, 0.56), lw=lw * 0.8)
        pk = waist - up * 0.14 * u + side * 0.10 * u
        pocket = smooth_path(ellipse_pts(pk[0], pk[1] + 0.10 * u, 0.12 * u, 0.09 * u, 14))
        D.shape(pocket, shade(DRESS, 1.06), line=shade(DRESS, 0.58), lw=lw * 0.8)
        flower(c, pk[0], pk[1] + 0.09 * u, 0.05 * u, petal=(255, 255, 255), center=SCARF)
    # оборка по подолу
    D.tapered([tuple(hem + side * (-0.50 * u) + up * 0.06 * u), tuple(hem + up * 0.03 * u), tuple(hem + side * (0.50 * u) + up * 0.06 * u)],
              lw, lw, shade(DRESS, 1.10), mid=lw * 2.6, alpha=0.9)
    folds(c, [[tuple(waist + side * 0.15 * u - up * 0.15 * u), tuple(hem + side * 0.26 * u + up * 0.06 * u)],
              [tuple(waist - side * 0.18 * u - up * 0.15 * u), tuple(hem - side * 0.32 * u + up * 0.06 * u)]], shade(DRESS, 0.62), 0.4, lw * 1.3)


def dots(c, x, y, r):
    c.drawCircle(x, y, r * 0.55, paint((255, 255, 255), 0.92))


def braid(c, R, base, sway, lw, side):
    D = Draw(c)
    pts = [base]
    for k in range(1, 5):
        pts.append((base[0] + side * R * 0.05 * k - sway * R * 0.12 * k, base[1] + R * 0.16 * k))
    for k in range(4):
        a, b = np.array(pts[k]), np.array(pts[k + 1])
        m = (a + b) / 2
        D.ellipse(m[0], m[1], R * 0.085, R * 0.11, HAIR, line=shade(HAIR, 0.55), lw=lw * 0.8)
    tip = pts[-1]
    D.ellipse(tip[0] - R * 0.06, tip[1], R * 0.07, R * 0.05, BOW, line=shade(BOW, 0.55), lw=lw * 0.7)
    D.ellipse(tip[0] + R * 0.06, tip[1], R * 0.07, R * 0.05, BOW, line=shade(BOW, 0.55), lw=lw * 0.7)
    c.drawCircle(tip[0], tip[1], R * 0.03, paint(shade(BOW, 0.8)))
    D.tapered([(tip[0], tip[1] + R * 0.02), (tip[0] - side * R * 0.02, tip[1] + R * 0.12)], R * 0.05, R * 0.01, HAIR)


def draw_head_back(c, R, t, p, lw):
    """Сзади: волосы за ушами, косички, узелок платочка с концами."""
    D = Draw(c)
    xb = -math.sin(t * 1.15) * R * 0.70
    sw = p.get("hair_sway", 0.0)
    hairback = smooth_path([(math.cos(a) * R * 1.04 + xb * 0.1, math.sin(a) * R * 1.02) for a in np.linspace(math.pi * 0.8, math.pi * 2.2, 22)] +
                           [(R * 0.85, R * 0.55), (-R * 0.85, R * 0.55)], tension=0.45)
    D.shape(hairback, shade(HAIR, 0.9), line=shade(HAIR, 0.55), lw=lw)
    for side in (-1, 1):
        bx = side * R * 0.86 + xb * 0.25
        if side * t < 0.75:
            braid(c, R, (bx, R * 0.35), sw, lw, side)
    ssw = p.get("scarf_sway", 0.0)
    knot = (xb - R * 0.10, R * 0.10)
    for k, (dx, ln) in enumerate(((-0.30, 0.55), (0.05, 0.45))):
        tip = (knot[0] + (dx - 0.35 - ssw * 0.6) * R, knot[1] + ln * R)
        mid = ((knot[0] + tip[0]) / 2 - ssw * R * 0.25, (knot[1] + tip[1]) / 2 + R * 0.04)
        pth, _ = tube([knot, mid, tip], [R * 0.20, R * 0.19, R * 0.06], n=14)
        D.shape(pth, shade(SCARF, 0.94 - 0.06 * k), line=shade(SCARF, 0.55), lw=lw)
    c.drawCircle(knot[0], knot[1], R * 0.12, paint(SCARF))
    c.drawCircle(knot[0], knot[1], R * 0.12, paint(shade(SCARF, 0.55), style="stroke", width=lw))


def draw_head_front(c, R, t, p, lw):
    D = Draw(c)
    xf = feat_center(t, R)
    # пряди у висков
    for side in (-1, 1):
        if side * t > -0.6:
            sx = xf + side * R * 0.80 * (1 - 0.3 * abs(t))
            D.tapered([(sx, -R * 0.30), (sx + side * R * 0.05, R * 0.05), (sx + side * R * 0.02, R * 0.30)], R * 0.10, R * 0.03, HAIR, mid=R * 0.11)
    # чёлка: мягкие пряди
    for dx, ln in ((-0.36, 0.20), (-0.16, 0.26), (0.06, 0.24), (0.26, 0.19)):
        x0 = xf + dx * R
        D.tapered([(x0 - R * 0.10, -R * 0.42), (x0 - R * 0.01, -R * (0.36 - ln * 0.5)), (x0 + R * 0.07, -R * (0.38 - ln))], R * 0.12, R * 0.02, HAIR, mid=R * 0.13)
    cap = scarf_cap(c, R, t, SCARF, shade(SCARF, 0.55), lw, pattern=dots, front_drop=0.50, back_drop=0.62, scale=1.10)
    # подвёрнутый край платочка — мягкий валик над чёлкой
    edge = [(x, -0.50 * R + 0.42 * R * ((x - xf) / R) ** 2) for x in np.linspace(xf - 0.78 * R, xf + 0.78 * R, 14)]
    edge = [(x, y) for x, y in edge if x * x + y * y < (1.08 * R) ** 2]
    D.tapered(edge, R * 0.05, R * 0.05, shade(SCARF, 1.08), mid=R * 0.09, alpha=0.95)
    D.tapered([(x, y + R * 0.045) for x, y in edge], R * 0.01, R * 0.01, shade(SCARF, 0.62), mid=R * 0.025, alpha=0.8)


def draw_head_backview(c, R, t, p, lw):
    D = Draw(c)
    hair_back_full(c, R, lw, HAIR, nape=0.5)
    sw = p.get("hair_sway", 0.0)
    for side in (-1, 1):
        braid(c, R, (side * R * 0.55, R * 0.40), sw, lw, side)
    # платочек сверху и узелок
    path = smooth_path([(math.cos(a) * R * 1.12, math.sin(a) * R * 1.12) for a in np.linspace(math.pi, 2 * math.pi, 20)] +
                       [(R * 1.05, R * 0.15), (0, R * 0.32), (-R * 1.05, R * 0.15)], tension=0.4)
    D.shape(path, SCARF, line=shade(SCARF, 0.55), lw=lw, shadow=(-R * 0.08, -R * 0.08, shade(SCARF, 0.84), R * 0.08))
    c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
    rng = np.random.default_rng(5)
    for i in range(18):
        dots(c, rng.uniform(-R, R), rng.uniform(-R, R * 0.3), R * 0.07)
    c.restore()
    ssw = p.get("scarf_sway", 0.0)
    for k, dx in enumerate((-0.25, 0.25)):
        tip = (dx * R - ssw * R * 0.4, R * 0.85)
        pth, _ = tube([(0, R * 0.28), (dx * R * 0.6, R * 0.55), tip], [R * 0.18, R * 0.17, R * 0.06], n=12)
        D.shape(pth, shade(SCARF, 0.94), line=shade(SCARF, 0.55), lw=lw)
    c.drawCircle(0, R * 0.28, R * 0.12, paint(SCARF))
    c.drawCircle(0, R * 0.28, R * 0.12, paint(shade(SCARF, 0.55), style="stroke", width=lw))


DESIGN = Design(
    name="yasmina", head_r=0.5, head_wx=1.02, head_wy=0.97,
    leg_len=0.96, thigh=0.46, shin=0.44, ankle_h=0.10, torso_len=0.74, neck_len=0.07,
    sh_w=0.58, sh_drop=0.12, hip_w=0.40, upper=0.36, fore=0.33, hand=0.21, arm_w=0.15,
    thigh_w=0.23, knee_w=0.19, ankle_w=0.15, sleeve_len=0.92,
    skin=SKIN, legwear=(166, 150, 206), shoe=(108, 196, 170), sole=(255, 250, 244), sleeve=DRESS,
    line_px=2.5,
    face=FaceStyle(skin=SKIN, line=(176, 116, 100), iris=(112, 70, 40), iris2=(204, 148, 88), lash=(60, 36, 32),
                   brow=(100, 62, 44), blush=(252, 128, 128), lip=(220, 116, 116), female=True, eye_size=1.22, eye_sep=0.38,
                   eye_y=0.10, mouth_y=0.58, nose_y=0.37, brow_th=0.85, lashes=2),
    draw_torso=draw_torso, draw_head_back=draw_head_back, draw_head_front=draw_head_front,
    draw_head_backview=draw_head_backview, hide_ears=True,
)
