"""Мама Лейла, около 30 лет. Спокойная, тёплая, мудрая; не читает нотаций — задаёт вопрос, показывает,
обнимает. Двигается плавно, говорит мягко и неторопливо.

Силуэт: пудрово-розовый хиджаб, мягко обрамляющий лицо и спадающий на плечи; длинное платье цвета
шалфея; светлый кремовый кардиган до бёдер; тёплые коричневые туфли.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube
from character import Design
from face import FaceStyle
from common_parts import torso_shape, folds
from family_parts import hijab_back, hijab_front

SKIN = (242, 204, 178)
HIJAB = (234, 184, 176)
HIJAB_LINE = (176, 120, 116)
DRESS = (138, 172, 146)
CARDI = (248, 236, 214)


def draw_torso(c, J, p, lw):
    u = p["u"]
    f = p.get("face", 1)
    D = Draw(c)
    sway = p.get("sway", 0.0)
    hip_h = -J["hip"][1] / u                      # высота таза над землёй (ед.)
    drop = min(1.52, hip_h - 0.06)
    kneel = max(0.0, 1.52 - drop)                 # присела — подол ложится шире
    path, ref = torso_shape(J, u, 0.74, 0.64, 1.36 + kneel * 0.9, drop, sway=sway * 0.22, flare=abs(sway) * 0.05 + kneel * 0.1, waist_up=0.30)
    D.shape(path, DRESS, line=shade(DRESS, 0.55), lw=lw, shadow=(-0.10 * u * f, -0.06 * u, shade(DRESS, 0.82), 0.06 * u),
            light=(0.06 * u * f, 0.05 * u, (226, 246, 226), 0.04 * u))
    up, side, waist, hem = ref["up"], ref["side"], ref["waist"], ref["hem_c"]
    ch, hip = J["chest"], J["hip"]
    back = p.get("back", 0)
    cd_hem = hip - up * 0.50 * u
    if back:
        panel = smooth_path([tuple(J["sh_f"] + side * (-0.08 * u)), tuple(J["sh_n"] + side * (0.08 * u)),
                             tuple(cd_hem + side * (0.52 * u)), tuple(cd_hem + side * (-0.52 * u))], tension=0.4)
        D.shape(panel, CARDI, line=shade(CARDI, 0.6), lw=lw, shadow=(-0.06 * u * f, -0.05 * u, shade(CARDI, 0.86), 0.04 * u))
    else:
        for sgn, k in ((-1, 0.96), (1, 1.0)):
            panel = smooth_path([tuple(ch + side * (sgn * 0.07 * u) + up * 0.02 * u), tuple(J["sh_n" if sgn > 0 else "sh_f"] + side * (sgn * 0.08 * u)),
                                 tuple(waist + side * (sgn * 0.40 * u)), tuple(cd_hem + side * (sgn * 0.50 * u)),
                                 tuple(cd_hem + side * (sgn * 0.14 * u) + up * 0.02 * u), tuple(ch + side * (sgn * 0.12 * u) - up * 0.45 * u)], tension=0.45)
            D.shape(panel, shade(CARDI, k), line=shade(CARDI, 0.6), lw=lw, shadow=(-0.06 * u * f, -0.05 * u, shade(CARDI, 0.86), 0.04 * u))
        # карман кардигана
        pk = waist - up * 0.12 * u + side * 0.30 * u
        D.tapered([tuple(pk + side * (-0.10 * u)), tuple(pk + side * (0.10 * u))], lw, lw, shade(CARDI, 0.65), mid=lw * 1.6, alpha=0.8)
    D.tapered([tuple(cd_hem + side * (-0.5 * u) + up * 0.05 * u), tuple(cd_hem + side * (0.5 * u) + up * 0.05 * u)], lw, lw, shade(CARDI, 0.78), mid=lw * 2, alpha=0.5)
    folds(c, [[tuple(hip + side * 0.22 * u - up * 0.6 * u), tuple(hem + side * 0.32 * u + up * 0.05 * u)],
              [tuple(hip - side * 0.25 * u - up * 0.65 * u), tuple(hem - side * 0.45 * u + up * 0.05 * u)],
              [tuple(hip + side * 0.02 * u - up * 0.8 * u), tuple(hem - side * 0.05 * u + up * 0.05 * u)]], shade(DRESS, 0.62), 0.45, lw * 1.4)


def hijab_pattern(c, R, t):
    # едва заметный узор-веточка по краю
    rng = np.random.default_rng(11)
    for i in range(10):
        x, y = rng.uniform(-1.3 * R, 1.3 * R), rng.uniform(0.9 * R, 2.2 * R)
        c.drawCircle(x, y, R * 0.025, paint((255, 236, 230), 0.6))


def draw_head_back(c, R, t, p, lw):
    hijab_back(c, R, t, p, lw, HIJAB, HIJAB_LINE)


def draw_head_front(c, R, t, p, lw):
    hijab_front(c, R, t, p, lw, HIJAB, HIJAB_LINE, SKIN, pattern=hijab_pattern)


def draw_head_backview(c, R, t, p, lw):
    hijab_front(c, R, t, p, lw, HIJAB, HIJAB_LINE, SKIN, back=True)


DESIGN = Design(
    name="leyla", head_r=0.5, head_wx=0.94, head_wy=1.07,
    leg_len=1.78, thigh=0.86, shin=0.84, ankle_h=0.10, torso_len=1.22, neck_len=0.14,
    sh_w=0.72, sh_drop=0.14, hip_w=0.50, upper=0.62, fore=0.56, hand=0.24, arm_w=0.155,
    thigh_w=0.25, knee_w=0.20, ankle_w=0.14, sleeve_len=0.94,
    skin=SKIN, legwear=(120, 100, 96), shoe=(150, 98, 70), sole=(110, 70, 50), sleeve=CARDI,
    line_px=2.4,
    face=FaceStyle(skin=SKIN, line=(170, 118, 100), iris=(104, 66, 40), iris2=(186, 134, 82), lash=(52, 34, 32),
                   brow=(92, 60, 46), blush=(240, 146, 140), lip=(210, 112, 116), female=True, eye_size=0.94, eye_sep=0.37,
                   eye_y=0.08, mouth_y=0.60, nose_y=0.36, brow_th=0.85, lashes=3, eye_shape=1.02),
    draw_torso=draw_torso, draw_head_back=draw_head_back, draw_head_front=draw_head_front,
    draw_head_backview=draw_head_backview, hide_ears=True, hide_legs=True,
)
