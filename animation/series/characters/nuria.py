"""Бабушка Нурия, 68 лет — спокойная, тёплая, с хитринкой. Говорит неторопливо, любит пословицы,
отвечает вопросом на вопрос. Силуэт: узорный кремовый платок с узлом сзади, очки-полумесяцы,
вязаный кардиган цвета охры поверх длинного сливового платья, мягкие тёмные туфли.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube
from character import Design
from face import FaceStyle
from common_parts import torso_shape, folds, scarf_cap, flower

SKIN = (234, 196, 170)
SCARF = (246, 232, 206)
DRESS = (128, 66, 104)
CARDI = (214, 150, 70)


def pattern(c, x, y, r):
    flower(c, x, y, r * 1.1, petal=(200, 90, 80), center=(90, 140, 80))


def draw_torso(c, J, p, lw):
    u = p["u"]
    f = p.get("face", 1)
    D = Draw(c)
    sway = p.get("sway", 0.0)
    path, ref = torso_shape(J, u, 0.80, 0.86, 1.30, 1.18, sway=sway * 0.2, flare=abs(sway) * 0.04, waist_up=0.22)
    D.shape(path, DRESS, line=shade(DRESS, 0.55), lw=lw, shadow=(-0.10 * u * f, -0.06 * u, shade(DRESS, 0.8), 0.06 * u),
            light=(0.06 * u * f, 0.05 * u, (240, 200, 230), 0.04 * u))
    up, side, waist, hem = ref["up"], ref["side"], ref["waist"], ref["hem_c"]
    ch, hip = J["chest"], J["hip"]
    # кардиган: открытая полочка спереди
    cd_hem = hip - up * 0.42 * u
    for sgn, k in ((-1, 0.92), (1, 1.0)):
        panel = smooth_path([tuple(ch + side * (sgn * 0.06 * u) + up * 0.02 * u), tuple(J["sh_n" if sgn > 0 else "sh_f"] + side * (sgn * 0.08 * u)),
                             tuple(waist + side * (sgn * 0.46 * u)), tuple(cd_hem + side * (sgn * 0.52 * u)),
                             tuple(cd_hem + side * (sgn * 0.12 * u) + up * 0.02 * u), tuple(ch + side * (sgn * 0.10 * u) - up * 0.40 * u)], tension=0.45)
        D.shape(panel, shade(CARDI, k), line=shade(CARDI, 0.55), lw=lw, shadow=(-0.06 * u * f, -0.05 * u, shade(CARDI, 0.82), 0.04 * u))
    for i in range(3):
        b = ch - up * (0.30 + 0.22 * i) * u + side * (0.16 * u)
        c.drawCircle(b[0], b[1], 0.035 * u, paint((120, 80, 50)))
    # вязка — рубчик по низу
    D.tapered([tuple(cd_hem + side * (-0.5 * u) + up * 0.05 * u), tuple(cd_hem + side * (0.5 * u) + up * 0.05 * u)], lw, lw, shade(CARDI, 0.7), mid=lw * 2, alpha=0.6)
    folds(c, [[tuple(hip + side * 0.2 * u - up * 0.5 * u), tuple(hem + side * 0.3 * u + up * 0.05 * u)],
              [tuple(hip - side * 0.25 * u - up * 0.55 * u), tuple(hem - side * 0.42 * u + up * 0.05 * u)]], shade(DRESS, 0.6), 0.45, lw * 1.4)


def draw_head_back(c, R, t, p, lw):
    D = Draw(c)
    xb = -math.sin(t * 1.15) * R * 0.70
    sw = p.get("scarf_sway", 0.0)
    drape = smooth_path([(-R * 1.08 + xb * 0.2, -R * 0.2), (-R * 1.05 + xb * 0.5, R * 0.6), (xb - R * 0.65 - sw * R * 0.2, R * 1.35),
                         (xb + R * 0.30, R * 1.45), (R * 0.85 + xb * 0.5, R * 1.10), (R * 1.04 + xb * 0.2, R * 0.45),
                         (R * 1.08, -R * 0.25), (0, -R * 1.12)], tension=0.5)
    D.shape(drape, shade(SCARF, 0.9), line=shade(SCARF, 0.55), lw=lw, shadow=(-R * 0.1, -R * 0.1, shade(SCARF, 0.8), R * 0.1))
    c.save(); c.clipPath(drape, skia.ClipOp.kIntersect, True)
    rng = np.random.default_rng(3)
    for i in range(14):
        pattern(c, rng.uniform(-R, R), rng.uniform(-R * 0.5, R * 1.4), R * 0.07)
    c.restore()
    knot = (xb - R * 0.20, R * 0.95)
    for k, (dx, ln) in enumerate(((-0.2, 0.55), (0.1, 0.45))):
        tip = (knot[0] + (dx - 0.25 - sw * 0.5) * R, knot[1] + ln * R)
        pth, _ = tube([knot, ((knot[0] + tip[0]) / 2, (knot[1] + tip[1]) / 2 + R * 0.04), tip], [R * 0.22, R * 0.2, R * 0.1], n=12)
        D.shape(pth, shade(SCARF, 0.93 - 0.05 * k), line=shade(SCARF, 0.55), lw=lw)


def draw_head_front(c, R, t, p, lw):
    xf = math.sin(t * 1.15) * R * 0.92
    D = Draw(c)
    # седая прядь
    D.tapered([(xf - R * 0.35, -R * 0.40), (xf - R * 0.05, -R * 0.33), (xf + R * 0.25, -R * 0.37)], R * 0.06, R * 0.04, (220, 216, 214), mid=R * 0.09)
    scarf_cap(c, R, t, SCARF, shade(SCARF, 0.55), lw, pattern=pattern, front_drop=0.42, back_drop=1.2, scale=1.08)


DESIGN = Design(
    name="nuria", head_r=0.5, head_wx=1.02, head_wy=1.0,
    leg_len=1.30, thigh=0.62, shin=0.60, ankle_h=0.10, torso_len=1.12, neck_len=0.10,
    sh_w=0.78, sh_drop=0.14, hip_w=0.50, upper=0.52, fore=0.48, hand=0.24, arm_w=0.18,
    thigh_w=0.26, knee_w=0.21, ankle_w=0.16, sleeve_len=0.90,
    skin=SKIN, legwear=(90, 66, 60), shoe=(70, 46, 40), sole=(50, 36, 30), sleeve=CARDI,
    line_px=2.6,
    face=FaceStyle(skin=SKIN, line=(160, 112, 96), iris=(90, 64, 46), iris2=(160, 120, 84), lash=(70, 50, 46),
                   brow=(170, 160, 156), blush=(236, 140, 130), lip=(190, 110, 104), female=True, eye_size=0.88, eye_sep=0.36,
                   eye_y=0.04, mouth_y=0.58, nose_y=0.33, brow_th=0.9, glasses=(176, 136, 70), wrinkles=True, lashes=0, eye_shape=1.05),
    draw_torso=draw_torso, draw_head_back=draw_head_back, draw_head_front=draw_head_front, hide_ears=True,
)
