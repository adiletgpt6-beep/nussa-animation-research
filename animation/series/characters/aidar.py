"""Айдар, 9 лет — старший брат, «главный агроном». Серьёзный книжник с чувством юмора,
немного всезнайка, поправляет очки, когда объясняет. Силуэт: растрёпанные волосы с хохолком,
круглые очки, зелёная футболка с листиком поверх бежевого лонгслива, брюки хаки, синие кеды.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube
from character import Design
from face import FaceStyle
from common_parts import torso_shape, folds

SKIN = (236, 196, 166)
HAIR = (44, 34, 38)
TEE = (98, 168, 84)
SHIRT = (232, 214, 182)


def draw_torso(c, J, p, lw):
    u = p["u"]
    f = p.get("face", 1)
    D = Draw(c)
    path, ref = torso_shape(J, u, 0.66, 0.56, 0.62, 0.12, waist_up=0.25)
    D.shape(path, TEE, line=shade(TEE, 0.55), lw=lw, shadow=(-0.10 * u * f, -0.06 * u, shade(TEE, 0.82), 0.05 * u),
            light=(0.06 * u * f, 0.05 * u, (220, 255, 200), 0.04 * u))
    up, side, waist = ref["up"], ref["side"], ref["waist"]
    ch = J["chest"]
    # листик на груди
    lc = ch - up * 0.30 * u + side * 0.08 * u
    leaf = smooth_path([tuple(lc + side * (-0.10 * u)), tuple(lc + up * 0.06 * u), tuple(lc + side * (0.10 * u)), tuple(lc - up * 0.06 * u)], tension=0.6)
    D.shape(leaf, (236, 246, 200), line=shade(TEE, 0.5), lw=lw * 0.7)
    D.tapered([tuple(lc + side * (-0.09 * u)), tuple(lc + side * (0.09 * u))], 1, 1, shade(TEE, 0.5), mid=2)
    # горловина лонгслива
    D.tapered([tuple(ref["neck_l"]), tuple(ch - up * 0.04 * u), tuple(ref["neck_r"])], lw, lw, SHIRT, mid=lw * 3)
    # карандаш за ухом — у головы; ремень
    D.tapered([tuple(ref["hem_c"] + up * 0.10 * u + side * (-0.32 * u)), tuple(ref["hem_c"] + up * 0.10 * u + side * (0.32 * u))], lw, lw, (120, 84, 60), mid=lw * 2.2)
    folds(c, [[tuple(waist + side * 0.1 * u), tuple(ref["hem_c"] + side * 0.16 * u + up * 0.12 * u)]], shade(TEE, 0.6), 0.4, lw * 1.2)


def hair_cap(c, R, t, lw, fringe_drop=0.32, spikes=6):
    xf = math.sin(t * 1.15) * R * 0.92
    D = Draw(c)
    pts = []
    xs = np.linspace(-1.45 * R, 1.45 * R, 60)
    for i, x in enumerate(xs):
        d = (x - xf) / R
        base = -fringe_drop * R + 0.45 * R * d * d
        if abs(d) < 0.9:  # зубцы чёлки
            ph = (d + 0.9) / 1.8 * spikes
            base += R * 0.10 * (abs((ph % 1.0) - 0.5) * 2) ** 1.6
        pts.append((x, min(base, 0.15 * R if (x - xf) * (1 if t >= 0 else -1) > 0 else 0.55 * R)))
    pts += [(1.45 * R, -2 * R), (-1.45 * R, -2 * R)]
    region = smooth_path(pts, tension=0.15)
    head = smooth_path([(math.cos(a) * R * 1.07 - t * R * 0.05, math.sin(a) * R * (1.08 if math.sin(a) < 0 else 0.98)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)])
    cap = skia.Op(head, region, skia.PathOp.kIntersect_PathOp)
    if cap is None:
        return
    D.shape(cap, HAIR, line=shade(HAIR, 0.6), lw=lw, shadow=(-R * 0.06, -R * 0.06, shade(HAIR, 0.7), R * 0.06))
    # блик на волосах
    c.save(); c.clipPath(cap, skia.ClipOp.kIntersect, True)
    D.tapered([(xf - R * 0.6, -R * 0.75), (xf - R * 0.1, -R * 0.92), (xf + R * 0.4, -R * 0.8)], R * 0.03, R * 0.03, (140, 130, 150), mid=R * 0.08, alpha=0.7)
    c.restore()


def draw_head_back(c, R, t, p, lw):
    D = Draw(c)
    xb = -math.sin(t * 1.15) * R * 0.6
    back = smooth_path([(math.cos(a) * R * 1.06 + xb * 0.15, math.sin(a) * R * 1.05 - R * 0.02) for a in np.linspace(math.pi * 0.85, math.pi * 2.15, 20)] +
                       [(xb, R * 0.35)], tension=0.4)
    D.shape(back, shade(HAIR, 0.9), line=shade(HAIR, 0.6), lw=lw)


def draw_head_front(c, R, t, p, lw):
    D = Draw(c)
    hair_cap(c, R, t, lw)
    # хохолок с вторичным движением
    sw = p.get("hair_sway", 0.0)
    xt = math.sin(t * 1.15) * R * 0.2 - R * 0.15
    base = (xt, -R * 1.02)
    tip = (xt - R * 0.25 - sw * R * 0.4, -R * 1.42)
    pth, _ = tube([base, ((base[0] + tip[0]) / 2 + R * 0.12, -R * 1.25), tip], [R * 0.24, R * 0.12, R * 0.02], n=14)
    D.shape(pth, HAIR, line=shade(HAIR, 0.6), lw=lw)


DESIGN = Design(
    name="aidar", head_r=0.5, head_wx=0.97, head_wy=1.0,
    leg_len=1.30, thigh=0.62, shin=0.60, ankle_h=0.10, torso_len=0.92, neck_len=0.12,
    sh_w=0.68, sh_drop=0.12, hip_w=0.42, upper=0.46, fore=0.43, hand=0.22, arm_w=0.15,
    thigh_w=0.22, knee_w=0.18, ankle_w=0.15, sleeve_len=0.93,
    skin=SKIN, legwear=(170, 150, 104), shoe=(64, 104, 196), sole=(250, 250, 250), sleeve=SHIRT,
    line_px=2.6,
    face=FaceStyle(skin=SKIN, line=(160, 108, 90), iris=(70, 46, 30), iris2=(150, 104, 64), lash=(40, 28, 28),
                   brow=(40, 30, 32), blush=(240, 130, 120), lip=(196, 110, 100), female=False, eye_size=1.0, eye_sep=0.36,
                   eye_y=0.04, mouth_y=0.56, nose_y=0.32, brow_th=1.15, glasses=(70, 60, 70), lashes=0),
    draw_torso=draw_torso, draw_head_back=draw_head_back, draw_head_front=draw_head_front,
)
