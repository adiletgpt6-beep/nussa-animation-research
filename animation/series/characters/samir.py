"""Самир, 9 лет — старший брат. Добрый, заботливый, любознательный, иногда озорной. Всегда носит
с собой лупу и блокнот, любит «исследовать» и составлять планы; когда смущается — чешет затылок.
Двигается энергично: быстрые шаги, приседает на корточки, показывает руками.

Силуэт: растрёпанные каштановые волосы с вихром, бирюзово-голубой свитшот с жёлтой нашивкой-
бумажным самолётиком, белый воротник футболки, тёмно-синие брюки, оранжевые кеды.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube
from character import Design
from face import FaceStyle
from common_parts import torso_shape, folds
from family_parts import feat_center, hair_mass, hair_back_full

SKIN = (238, 198, 168)
HAIR = (78, 50, 38)
SWEAT = (82, 160, 196)
PATCH = (255, 206, 84)


def draw_torso(c, J, p, lw):
    u = p["u"]
    f = p.get("face", 1)
    D = Draw(c)
    path, ref = torso_shape(J, u, 0.66, 0.58, 0.64, 0.14, waist_up=0.24)
    D.shape(path, SWEAT, line=shade(SWEAT, 0.55), lw=lw, shadow=(-0.10 * u * f, -0.06 * u, shade(SWEAT, 0.82), 0.05 * u),
            light=(0.06 * u * f, 0.05 * u, (214, 240, 255), 0.04 * u))
    up, side, waist = ref["up"], ref["side"], ref["waist"]
    ch = J["chest"]
    hem = ref["hem_c"]
    # резинка свитшота
    D.tapered([tuple(hem + up * 0.06 * u + side * (-0.33 * u)), tuple(hem + up * 0.06 * u + side * (0.33 * u))], lw, lw, shade(SWEAT, 0.8), mid=lw * 3.2, alpha=0.9)
    if not p.get("back"):
        D.tapered([tuple(ref["neck_l"]), tuple(ch - up * 0.05 * u), tuple(ref["neck_r"])], lw, lw, (250, 250, 246), mid=lw * 3)
        pc = ch - up * 0.32 * u + side * 0.12 * u
        plane = smooth_path([tuple(pc + side * (-0.12 * u) + up * 0.02 * u), tuple(pc + side * (0.13 * u) + up * 0.07 * u),
                             tuple(pc + side * (-0.02 * u) - up * 0.06 * u)], tension=0.1)
        D.shape(plane, PATCH, line=shade(PATCH, 0.6), lw=lw * 0.7)
        D.tapered([tuple(pc + side * (-0.12 * u) + up * 0.02 * u), tuple(pc + side * (0.05 * u) + up * 0.01 * u)], 1, 1, shade(PATCH, 0.6), mid=1.6)
    folds(c, [[tuple(waist + side * 0.12 * u), tuple(hem + side * 0.18 * u + up * 0.12 * u)],
              [tuple(ch - up * 0.2 * u - side * 0.2 * u), tuple(waist - side * 0.12 * u)]], shade(SWEAT, 0.6), 0.4, lw * 1.2)


def draw_head_back(c, R, t, p, lw):
    D = Draw(c)
    xb = -math.sin(t * 1.15) * R * 0.6
    back = smooth_path([(math.cos(a) * R * 1.08 + xb * 0.15, math.sin(a) * R * 1.07 - R * 0.02) for a in np.linspace(math.pi * 0.85, math.pi * 2.15, 22)] +
                       [(xb, R * 0.30)], tension=0.4)
    D.shape(back, shade(HAIR, 0.9), line=shade(HAIR, 0.55), lw=lw)


def cowlick(c, R, t, p, lw, x0, y0):
    D = Draw(c)
    sw = p.get("hair_sway", 0.0)
    base = (x0, y0)
    tip = (x0 + R * 0.22 - sw * R * 0.35, y0 - R * 0.36)
    pth, _ = tube([base, (x0 + R * 0.02 - sw * R * 0.1, y0 - R * 0.24), tip], [R * 0.20, R * 0.10, R * 0.02], n=14)
    D.shape(pth, HAIR, line=shade(HAIR, 0.55), lw=lw)


def draw_head_front(c, R, t, p, lw):
    hair_mass(c, R, t, lw, HAIR, fringe_drop=0.36, clumps=6, side_len=0.30, seed=4, volume=1.10)
    xf = feat_center(t, R)
    cowlick(c, R, t, p, lw, xf * 0.25 + R * 0.10, -R * 1.02)
    # веснушки
    D = Draw(c)
    for s in (-1, 1):
        cx = xf * 0.9 + s * R * 0.42 * (1 - 0.3 * abs(t))
        for k in range(3):
            c.drawCircle(cx + (k - 1) * R * 0.06, R * 0.30 + (k % 2) * R * 0.03, R * 0.014, paint((196, 128, 96), 0.55))


def draw_head_backview(c, R, t, p, lw):
    hair_back_full(c, R, lw, HAIR, nape=0.35)
    cowlick(c, R, t, p, lw, R * 0.05, -R * 1.02)


DESIGN = Design(
    name="samir", head_r=0.5, head_wx=0.98, head_wy=1.0,
    leg_len=1.28, thigh=0.62, shin=0.59, ankle_h=0.10, torso_len=0.90, neck_len=0.11,
    sh_w=0.66, sh_drop=0.12, hip_w=0.42, upper=0.45, fore=0.42, hand=0.22, arm_w=0.155,
    thigh_w=0.23, knee_w=0.19, ankle_w=0.155, sleeve_len=0.95,
    skin=SKIN, legwear=(66, 78, 120), shoe=(238, 140, 66), sole=(252, 250, 246), sleeve=SWEAT,
    line_px=2.5,
    face=FaceStyle(skin=SKIN, line=(166, 110, 92), iris=(82, 52, 32), iris2=(166, 116, 70), lash=(44, 30, 28),
                   brow=(70, 46, 36), blush=(240, 136, 120), lip=(200, 112, 102), female=False, eye_size=1.08, eye_sep=0.37,
                   eye_y=0.07, mouth_y=0.57, nose_y=0.34, brow_th=1.15, lashes=0),
    draw_torso=draw_torso, draw_head_back=draw_head_back, draw_head_front=draw_head_front,
    draw_head_backview=draw_head_backview,
)
