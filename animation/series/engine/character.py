"""2D-персонаж: скелет с FK/IK, сгибающиеся конечности («трубки» по кривой), кисти с пальцами,
голова с поворотом (yaw), одежда и волосы через функции дизайна, мягкая светотень, сжатие/растяжение.

Локальная система: начало — точка на земле между стоп, ось y вниз, единица — высота головы `u` пикселей.
Персонаж нарисован смотрящим вправо; face=-1 — зеркально.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, tube, Draw, shade, ellipse_pts, curve_through, col
from face import draw_face, mouth_vec

HAND_PRESETS = {
    "relax": dict(curl=0.35, spread=0.15, thumb=0.3),
    "open": dict(curl=0.05, spread=0.55, thumb=0.0),
    "fist": dict(curl=1.0, spread=0.0, thumb=0.9),
    "grip": dict(curl=0.75, spread=0.05, thumb=0.7),
    "point": dict(curl=1.0, spread=0.0, thumb=0.8, index=0.0),
    "wave": dict(curl=0.0, spread=0.6, thumb=0.1),
    "pinch": dict(curl=0.55, spread=0.0, thumb=0.6, index=0.45),
}


def lerp(a, b, t):
    return a + (b - a) * t


def two_bone_ik(root, target, l1, l2, bend_dir):
    """Плоский IK: возвращает (локоть/колено, конец). bend_dir=+1/-1 — сторона сгиба."""
    r = np.array(root, float); tg = np.array(target, float)
    d = tg - r
    dist = np.linalg.norm(d)
    dist_c = min(max(dist, 1e-4), (l1 + l2) * 0.999)
    a = math.atan2(d[1], d[0])
    cos_a = (l1 * l1 + dist_c * dist_c - l2 * l2) / (2 * l1 * dist_c)
    cos_a = max(-1, min(1, cos_a))
    ang = a - bend_dir * math.acos(cos_a)
    mid = r + l1 * np.array([math.cos(ang), math.sin(ang)])
    end = r + d / max(dist, 1e-4) * dist_c
    return mid, end


def fk(root, a1, l1, a2, l2):
    """Углы от вертикали вниз (+ вперёд, т. е. вправо). a2 — относительный сгиб."""
    r = np.array(root, float)
    m = r + l1 * np.array([math.sin(a1), math.cos(a1)])
    e = m + l2 * np.array([math.sin(a1 + a2), math.cos(a1 + a2)])
    return m, e


class Design:
    """Спецификация внешности (пропорции в единицах высоты головы)."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def draw_hand(c, wrist, angle, size, hp, skin, line, near=True, face_sign=1):
    """Кисть: ладонь + 3 пальца + большой. angle — направление кисти (рад), hp — параметры."""
    D = Draw(c)
    curl, spread, thumb = hp.get("curl", 0.3), hp.get("spread", 0.2), hp.get("thumb", 0.3)
    c.save()
    c.translate(*wrist)
    c.rotate(math.degrees(angle) - 90)
    s = size
    palm = smooth_path(ellipse_pts(0, s * 0.38, s * 0.30, s * 0.36, 16))
    fing = []
    for i, off in enumerate((-0.18, 0.0, 0.18)):
        cu = curl if not (i == 0 and "index" in hp) else hp["index"]
        base = np.array([off * s * (1 + spread), s * 0.62])
        a0 = off * (0.6 + spread * 1.2)
        L1, L2 = s * 0.30 * (0.9 if i != 1 else 1.0), s * 0.24
        p1 = base + L1 * np.array([math.sin(a0), math.cos(a0)])
        a1 = a0 + cu * 1.5
        p2 = p1 + L2 * np.array([math.sin(-a1 * 0.0 + a0 * 0.3), math.cos(a1)]) if cu < 0.01 else p1 + L2 * np.array([-math.sin(a1) * 0.6 + math.sin(a0), math.cos(a1)])
        fing.append((base, p1, p2))
    tb = np.array([-s * 0.26, s * 0.22])
    ta = -0.9 + thumb * 1.1
    t1 = tb + s * 0.26 * np.array([math.sin(ta), math.cos(ta)])
    t2 = t1 + s * 0.2 * np.array([math.sin(ta + thumb * 0.9), math.cos(ta + thumb * 0.9)])
    outline_c = line
    # контур под заливкой (утолщение) -> аккуратная линия вокруг
    for base, p1, p2 in fing:
        pth, _ = tube([base, p1, p2], [s * 0.2, s * 0.17, s * 0.15], n=10)
        c.drawPath(pth, paint(outline_c, style="stroke", width=3.4))
    pth, _ = tube([tb, t1, t2], [s * 0.22, s * 0.18, s * 0.15], n=10)
    c.drawPath(pth, paint(outline_c, style="stroke", width=3.4))
    c.drawPath(palm, paint(outline_c, style="stroke", width=3.4))
    for base, p1, p2 in fing:
        pth, _ = tube([base, p1, p2], [s * 0.2, s * 0.17, s * 0.15], n=10)
        c.drawPath(pth, paint(skin))
    pth, _ = tube([tb, t1, t2], [s * 0.22, s * 0.18, s * 0.15], n=10)
    c.drawPath(pth, paint(skin))
    c.drawPath(palm, paint(skin))
    c.drawOval(skia.Rect(-s * 0.2, s * 0.25, s * 0.15, s * 0.55), paint(shade(skin, 0.85), 0.5, blur=s * 0.08))
    c.restore()


class Character:
    def __init__(self, design):
        self.d = design

    # ---------------------------------------------------------------- скелет
    def skeleton(self, p):
        d = self.d
        u = 1.0
        crouch = p.get("crouch", 0.0)
        lean = p.get("lean", 0.0)
        hip_y = -(d.leg_len - crouch) + p.get("bob", 0.0)
        hip = np.array([p.get("hip_x", 0.0), hip_y])
        torso = d.torso_len
        chest = hip + torso * np.array([math.sin(lean), -math.cos(lean)])
        neck_top = chest + d.neck_len * np.array([math.sin(lean + p.get("neck_lean", 0) ), -math.cos(lean + p.get("neck_lean", 0))])
        head_c = neck_top + d.head_r * 0.85 * np.array([math.sin(lean + p.get("neck_lean", 0)), -math.cos(lean + p.get("neck_lean", 0))])
        J = {"hip": hip, "chest": chest, "neck": neck_top, "head": head_c}
        tw = p.get("twist", 0.0)
        for side, sx in (("n", 1), ("f", -1)):
            # плечи: в 3/4 ближнее — вперёд, дальнее — назад
            sh = chest + np.array([sx * d.sh_w * 0.35 + tw * sx * 0.1, d.sh_drop]) + lean * np.array([0.0, 0.0])
            J["sh_" + side] = sh
            ik_w = p.get("arm_ik_" + side, 0.0)
            el_fk, wr_fk = fk(sh, p.get("arm_" + side, 0.05 * sx) + lean, d.upper, p.get("elbow_" + side, 0.25), d.fore)
            if ik_w > 0 and ("hand_t_" + side) in p:
                el_ik, wr_ik = two_bone_ik(sh, p["hand_t_" + side], d.upper, d.fore, -1)
                el = el_fk * (1 - ik_w) + el_ik * ik_w
                wr = wr_fk * (1 - ik_w) + wr_ik * ik_w
            else:
                el, wr = el_fk, wr_fk
            J["el_" + side], J["wr_" + side] = el, wr
            hp_ = hip + np.array([sx * d.hip_w * 0.3, 0.0])
            J["hp_" + side] = hp_
            ft = p.get("foot_" + side, (sx * d.hip_w * 0.25, 0.0))
            ft = np.array(ft, float) + np.array([0, -d.ankle_h])
            kn, an = two_bone_ik(hp_, ft, d.thigh, d.shin, +1)
            J["kn_" + side], J["an_" + side] = kn, an
        return J

    # ---------------------------------------------------------------- рисование
    def draw(self, c, p):
        d = self.d
        J = self.skeleton(p)
        u = p["u"]
        face = p.get("face", 1)
        J = {k: v * u for k, v in J.items()}
        c.save()
        c.translate(p["x"], p["y"])
        # сжатие-растяжение относительно стоп
        sx_, sy_ = p.get("sx", 1.0), p.get("sy", 1.0)
        c.scale(face * sx_, sy_)
        # контактная тень
        c.drawOval(skia.Rect(-0.75 * u, -0.08 * u, 0.75 * u, 0.08 * u), paint((40, 30, 45), 0.22, blur=0.08 * u))
        line_w = d.line_px
        self._limb_leg(c, J, "f", p, line_w, far=True)
        self._limb_arm(c, J, "f", p, line_w, far=True)
        if hasattr(d, "draw_back"):
            d.draw_back(c, J, p, line_w)
        self._limb_leg(c, J, "n", p, line_w, far=False)
        d.draw_torso(c, J, p, line_w)
        self._head(c, J, p, line_w, u)
        self._limb_arm(c, J, "n", p, line_w, far=False)
        if hasattr(d, "draw_front"):
            d.draw_front(c, J, p, line_w)
        c.restore()
        return J

    def _limb_leg(self, c, J, side, p, lw, far):
        d = self.d
        u = p["u"]
        k = 0.88 if far else 1.0
        hp_, kn, an = J["hp_" + side], J["kn_" + side], J["an_" + side]
        pant = shade(d.legwear, 0.86) if far else d.legwear
        path, C = tube([hp_, kn, an], [d.thigh_w * u, d.knee_w * u, d.ankle_w * u], n=22)
        D = Draw(c)
        D.shape(path, pant, line=shade(d.legwear, 0.55), lw=lw, shadow=(-0.05 * u * p.get('face', 1), -0.04 * u, shade(pant, 0.8), 0.03 * u))
        # обувь
        fa = p.get("foot_ang_" + side, 0.0)
        c.save()
        c.translate(*an)
        c.rotate(math.degrees(fa))
        c.scale(u * 1.25, u * 1.25)
        shoe = smooth_path([(-0.12, -0.02), (-0.13, d.ankle_h * 0.9), (0.06, d.ankle_h * 1.05), (0.30, d.ankle_h * 0.95),
                            (0.34, d.ankle_h * 0.5), (0.22, -0.01), (0.0, -0.06)], tension=0.6)
        shc = shade(d.shoe, 0.85) if far else d.shoe
        D.shape(shoe, shc, line=shade(d.shoe, 0.5), lw=lw / (u * 1.25), shadow=(0.0, -0.03, shade(shc, 0.78), 0.02))
        sole = smooth_path([(-0.13, d.ankle_h * 0.8), (0.33, d.ankle_h * 0.8), (0.33, d.ankle_h * 1.05), (-0.12, d.ankle_h * 1.02)], tension=0.4)
        c.drawPath(sole, paint(d.sole))
        c.restore()

    def _limb_arm(self, c, J, side, p, lw, far):
        d = self.d
        u = p["u"]
        sh, el, wr = J["sh_" + side], J["el_" + side], J["wr_" + side]
        sleeve = shade(d.sleeve, 0.86) if far else d.sleeve
        skin = shade(d.skin, 0.88) if far else d.skin
        D = Draw(c)
        # предплечье с кожей у запястья, рукав — до cuff
        aw = d.arm_w * u
        armpath, C = tube([sh, el, wr], [aw * 1.05, aw * 0.95, aw * 0.8], n=22)
        D.shape(armpath, skin, line=shade(d.skin, 0.6), lw=lw)
        cut = int(len(C) * d.sleeve_len)
        sp, _ = tube([C[0], C[cut // 2], C[cut]], [aw * 1.25, aw * 1.15, aw * 1.12], n=14)
        D.shape(sp, sleeve, line=shade(d.sleeve, 0.55), lw=lw, shadow=(-0.04 * u * p.get('face', 1), -0.03 * u, shade(sleeve, 0.8), 0.03 * u))
        # кисть
        dirv = C[-1] - C[-4]
        ang = math.atan2(dirv[1], dirv[0]) + p.get("wrist_" + side, 0.0)
        hp = p.get("hand_" + side, "relax")
        hp = HAND_PRESETS.get(hp, hp) if isinstance(hp, str) else hp
        draw_hand(c, C[-1], ang, d.hand * u, hp, skin, shade(d.skin, 0.6))
        if p.get("hold_" + side):
            p["hold_" + side](c, C[-1], ang, u)

    def _head(self, c, J, p, lw, u):
        d = self.d
        hc = J["head"]
        R = d.head_r * u
        t = p.get("head_yaw", 0.45)
        c.save()
        c.translate(*hc)
        c.rotate(math.degrees(p.get("head_tilt", 0.0) + p.get("lean", 0) * 0.3))
        hsx, hsy = p.get("head_sx", 1.0), p.get("head_sy", 1.0)
        c.scale(hsx, hsy)
        # шея
        D = Draw(c)
        neck = smooth_path([(-R * 0.26, R * 0.55), (R * 0.24, R * 0.55), (R * 0.22, R * 1.25), (-R * 0.22, R * 1.25)], tension=0.3)
        c.drawPath(neck, paint(shade(d.skin, 0.85)))
        if hasattr(d, "draw_head_back"):
            d.draw_head_back(c, R, t, p, lw)
        # форма головы: круг + щёки + подбородок, смещённые по yaw
        pts = []
        for i in range(36):
            a = 2 * math.pi * i / 36
            x, y = math.cos(a), math.sin(a)
            r = R * (1.0 + (0.06 * max(0, y)) * (1 + 0.5 * abs(x)))
            xx = x * r * d.head_wx
            yy = y * r * d.head_wy
            if y > 0:  # щека смещается в сторону взгляда
                xx += t * R * 0.10 * y
            pts.append((xx, yy))
        head = smooth_path(pts)
        f = p.get("face", 1)
        D.shape(head, d.skin, line=shade(d.skin, 0.62), lw=lw * 1.1, shadow=(-R * 0.10 * f, -R * 0.08, shade(d.skin, 0.86), R * 0.10),
                light=(R * 0.08 * f, R * 0.08, (255, 240, 225), R * 0.06))
        # ухо
        ex = math.sin(-1.65 + t * 1.15) * R * d.head_wx * 0.95
        if math.cos(-1.65 + t * 1.15) > -0.25 and not getattr(d, "hide_ears", False):
            ear = smooth_path(ellipse_pts(ex, R * 0.12, R * 0.13, R * 0.19, 14))
            D.shape(ear, d.skin, line=shade(d.skin, 0.62), lw=lw)
        st = dict(p.get("face_st", {}))
        if "mouth" not in st:
            st["mouth"] = mouth_vec({"X": 1})
        draw_face(c, R, d.face, st, t, p.get("head_pitch", 0.0))
        if hasattr(d, "draw_head_front"):
            d.draw_head_front(c, R, t, p, lw)
        c.restore()
