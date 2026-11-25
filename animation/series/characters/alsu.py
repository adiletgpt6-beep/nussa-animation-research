"""Алсу, 6 лет — главная героиня. Любознательная, нетерпеливая мечтательница, разговаривает с растениями.

Силуэт: круглая голова, жёлтый платочек с узелком и двумя «хвостиками», мятное платье-трапеция,
фартук с большим карманом, синие легинсы, красные кеды.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, Draw, shade, ellipse_pts, tube
from character import Design
from face import FaceStyle
from common_parts import torso_shape, folds, scarf_cap, flower

SKIN = (246, 208, 182)
SCARF = (255, 196, 64)
DRESS = (88, 186, 168)
APRON = (255, 244, 214)


def draw_torso(c, J, p, lw):
    u = p["u"]
    f = p.get("face", 1)
    D = Draw(c)
    sway = p.get("sway", 0.0)
    path, ref = torso_shape(J, u, 0.60, 0.50, 1.02, 0.40, sway=sway * 0.25, flare=abs(sway) * 0.05, waist_up=0.30)
    D.shape(path, DRESS, line=shade(DRESS, 0.55), lw=lw, shadow=(-0.10 * u * f, -0.06 * u, shade(DRESS, 0.82), 0.05 * u),
            light=(0.06 * u * f, 0.05 * u, (210, 255, 240), 0.04 * u))
    up, side, waist, hem = ref["up"], ref["side"], ref["waist"], ref["hem_c"]
    # пояс-завязка фартука и фартук только на юбке
    ap = smooth_path([tuple(waist + side * (-0.20 * u)), tuple(waist + side * (0.26 * u)),
                      tuple(hem + up * (0.10 * u) + side * (0.36 * u)), tuple(hem + up * (0.07 * u) + side * (0.02 * u)),
                      tuple(hem + up * (0.10 * u) + side * (-0.28 * u))], tension=0.5)
    D.shape(ap, APRON, line=shade(APRON, 0.62), lw=lw * 0.9, shadow=(-0.05 * u * f, -0.04 * u, shade(APRON, 0.86), 0.03 * u))
    D.tapered([tuple(waist + side * (-0.30 * u)), tuple(waist + side * (0.32 * u))], lw * 1.6, lw * 1.6, (240, 120, 110), mid=lw * 2.2)
    pk = waist - up * (0.24 * u) + side * (0.05 * u)
    pocket = smooth_path(ellipse_pts(pk[0], pk[1], 0.13 * u, 0.09 * u, 14))
    D.shape(pocket, shade(APRON, 0.96), line=shade(APRON, 0.6), lw=lw * 0.8)
    flower(c, pk[0] + 0.04 * u, pk[1] - 0.01 * u, 0.045 * u, petal=(255, 150, 150), center=SCARF)
    # воротничок «питер пэн»
    ch = J["chest"]
    for sgn in (-1, 1):
        cl = smooth_path([tuple(ch + up * 0.01 * u), tuple(ch + side * (sgn * 0.16 * u) - up * 0.02 * u),
                          tuple(ch + side * (sgn * 0.12 * u) - up * 0.10 * u), tuple(ch - up * 0.06 * u)], tension=0.5)
        D.shape(cl, (255, 255, 255), line=shade(DRESS, 0.55), lw=lw * 0.8)
    folds(c, [[tuple(waist + side * 0.15 * u - up * 0.15 * u), tuple(hem + side * 0.25 * u + up * 0.05 * u)],
              [tuple(waist - side * 0.18 * u - up * 0.15 * u), tuple(hem - side * 0.32 * u + up * 0.05 * u)]], shade(DRESS, 0.6), 0.4, lw * 1.3)


def scarf_pattern(c, x, y, r):
    flower(c, x, y, r, petal=(255, 255, 255), center=(255, 150, 60))


def draw_head_back(c, R, t, p, lw):
    """Платок сзади: мягкая драпировка до плеч, узелок и два конца (вторичное движение — p['scarf_sway'])."""
    D = Draw(c)
    xb = -math.sin(t * 1.15) * R * 0.70
    sw = p.get("scarf_sway", 0.0)
    drape = smooth_path([(-R * 1.04 + xb * 0.2, -R * 0.2), (-R * 1.0 + xb * 0.5, R * 0.6), (xb - R * 0.55 - sw * R * 0.2, R * 1.30),
                         (xb + R * 0.25 - sw * R * 0.15, R * 1.40), (R * 0.80 + xb * 0.5, R * 1.05), (R * 1.0 + xb * 0.2, R * 0.45),
                         (R * 1.04, -R * 0.25), (0, -R * 1.10)], tension=0.5)
    D.shape(drape, shade(SCARF, 0.90), line=shade(SCARF, 0.55), lw=lw, shadow=(-R * 0.1, -R * 0.1, shade(SCARF, 0.8), R * 0.1))
    knot = (xb - R * 0.15, R * 0.95)
    for k, (dx, ln) in enumerate(((-0.25, 0.75), (0.08, 0.62))):
        tip = (knot[0] + (dx - 0.30 - sw * 0.7) * R, knot[1] + ln * R - abs(sw) * R * 0.15)
        mid = ((knot[0] + tip[0]) / 2 - sw * R * 0.3, (knot[1] + tip[1]) / 2 + R * 0.05)
        pth, _ = tube([knot, mid, tip], [R * 0.24, R * 0.22, R * 0.08], n=16)
        D.shape(pth, shade(SCARF, 0.95 - 0.06 * k), line=shade(SCARF, 0.55), lw=lw)
    c.drawCircle(knot[0], knot[1], R * 0.14, paint(SCARF))
    c.drawCircle(knot[0], knot[1], R * 0.14, paint(shade(SCARF, 0.55), style="stroke", width=lw))


def draw_head_front(c, R, t, p, lw):
    D = Draw(c)
    xf = math.sin(t * 1.15) * R * 0.92
    # чёлка из-под платка
    hair = (92, 52, 36)
    for k, dx in enumerate((-0.30, -0.08, 0.16)):
        x0 = xf + dx * R
        D.tapered([(x0 - R * 0.10, -R * 0.36), (x0, -R * 0.25), (x0 + R * 0.08, -R * 0.14)], R * 0.10, R * 0.02, hair, mid=R * 0.12)
    scarf_cap(c, R, t, SCARF, shade(SCARF, 0.55), lw, pattern=scarf_pattern, front_drop=0.40, back_drop=1.2, scale=1.08)


DESIGN = Design(
    name="alsu", head_r=0.5, head_wx=1.0, head_wy=0.98,
    leg_len=1.02, thigh=0.49, shin=0.47, ankle_h=0.10, torso_len=0.78, neck_len=0.08,
    sh_w=0.62, sh_drop=0.12, hip_w=0.40, upper=0.38, fore=0.35, hand=0.21, arm_w=0.15,
    thigh_w=0.24, knee_w=0.19, ankle_w=0.15, sleeve_len=0.93,
    skin=SKIN, legwear=(84, 96, 168), shoe=(220, 72, 64), sole=(255, 248, 240), sleeve=DRESS,
    line_px=2.6,
    face=FaceStyle(skin=SKIN, line=(170, 110, 96), iris=(120, 72, 40), iris2=(196, 140, 84), lash=(58, 34, 32),
                   brow=(96, 58, 40), blush=(250, 120, 120), lip=(214, 112, 110), female=True, eye_size=1.18, eye_sep=0.38,
                   eye_y=0.06, mouth_y=0.56, nose_y=0.34, brow_th=0.9, lashes=2),
    draw_torso=draw_torso, draw_head_back=draw_head_back, draw_head_front=draw_head_front, hide_ears=True,
)
