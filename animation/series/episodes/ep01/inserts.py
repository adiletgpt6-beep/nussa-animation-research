"""Вставки крупным планом (рисуются на весь кадр 1920×1080): руки, семечко, земля, капли, корешок в разрезе,
росток, лупа, расписание на холодильнике, ленточка на стебле. k — прогресс действия 0..1, t — время серии.
Библиотечные: повторно используются в следующих сериях (руки героев, земля, капли).
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, poly_path, Draw, shade, mix, gradient_rect, radial, ellipse_pts, tube, col, W, H
from character import draw_hand, HAND_PRESETS, Character
from face import mouth_vec
import leyla, samir, yasmina

SOIL = (110, 76, 56)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def bokeh(c, base, spots, seed=1, t=0.0):
    gradient_rect(c, (0, 0, W, H), [(shade(base, 1.05), 0.0), (base, 0.6), (shade(base, 0.9), 1.0)])
    rng = np.random.default_rng(seed)
    for i in range(26):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 150)
        cc = spots[i % len(spots)]
        c.drawCircle(x + math.sin(t * 0.3 + i) * 10, y, r, paint(cc, rng.uniform(0.10, 0.28), blur=r * 0.25))


def seed_shape(c, x, y, s, ang=0.0, root=0.0, t=0.0):
    D = Draw(c)
    c.save(); c.translate(x, y); c.rotate(ang)
    if root > 0:
        L = 120 * s * root
        pts = [(0, 30 * s), (8 * s, 30 * s + L * 0.4), (-6 * s, 30 * s + L * 0.75), (4 * s, 30 * s + L)]
        D.tapered(pts, 7 * s, 1.5 * s, (250, 246, 232))
        D.tapered(pts, 3 * s, 0.5 * s, (220, 210, 190), alpha=0.6)
    body = smooth_path([(0, -38 * s), (18 * s, -12 * s), (16 * s, 22 * s), (0, 34 * s), (-16 * s, 22 * s), (-18 * s, -12 * s)], tension=0.55)
    D.shape(body, (64, 60, 66), line=(30, 28, 34), lw=2.4 * s, shadow=(-6 * s, -4 * s, (44, 40, 46), 4 * s))
    c.save(); c.clipPath(body, skia.ClipOp.kIntersect, True)
    for dx in (-9, 0, 9):
        D.tapered([(dx * s, -34 * s), (dx * 1.2 * s, 0), (dx * s, 32 * s)], 2.4 * s, 2.4 * s, (226, 222, 214), alpha=0.85, mid=3.6 * s)
    c.restore()
    D.tapered([(-6 * s, -24 * s), (-10 * s, 0)], 3 * s, 1 * s, (255, 255, 255), alpha=0.6)
    c.restore()


def sleeve_cuff(c, x, y, w, ang, color):
    D = Draw(c)
    c.save(); c.translate(x, y); c.rotate(math.degrees(ang))
    pth = smooth_path([(-w / 2, 0), (w / 2, 0), (w * 0.55, 600), (-w * 0.55, 600)], tension=0.2)
    D.shape(pth, color, line=shade(color, 0.6), lw=3, shadow=(-w * 0.15, 0, shade(color, 0.85), 10))
    D.tapered([(-w / 2, 16), (w / 2, 16)], 4, 4, shade(color, 0.8), alpha=0.6)
    c.restore()


# ------------------------------------------------------------------ ладонь мамы с семечком
def palm_seed(c, t, k, root=0.0, evening=False):
    base = (250, 226, 196) if not evening else (236, 180, 140)
    bokeh(c, base, [(255, 255, 240), (250, 200, 160), (200, 230, 210)] if not evening else [(255, 200, 140), (255, 160, 120), (255, 230, 180)], 3, t)
    rise = 40 * (1 - ease(k * 3))
    wx, wy = 900, 1180 + rise
    s = 760
    draw_hand(c, (wx, wy), -math.pi / 2 + 0.08, s, dict(curl=0.12, spread=0.45, thumb=0.05), leyla.SKIN, shade(leyla.SKIN, 0.6))
    sleeve_cuff(c, wx, wy + 40, 360, 0.08, leyla.CARDI)
    px, py = wx - 20, wy - s * 0.40
    c.drawOval(skia.Rect(px - 70, py + 10, px + 70, py + 40), paint((120, 70, 60), 0.25, blur=14))
    seed_shape(c, px, py, 2.4, ang=-20 + 4 * math.sin(t * 1.4), root=root, t=t)
    if k > 0.3 and root <= 0:
        for i in range(5):
            a = t * 1.5 + i * 1.26
            r = 120 + 20 * math.sin(t * 3 + i)
            c.drawCircle(px + math.cos(a) * r, py + math.sin(a) * r * 0.6, 4 + 3 * abs(math.sin(t * 4 + i)), paint((255, 252, 230), 0.7 * ease((k - 0.3) * 3)))


# ------------------------------------------------------------------ земля крупно
def soil_surface(c, wet=0.0, seed=4, hole=0.0, horizon=0.0):
    sky_h = int(H * horizon)
    if sky_h > 0:
        gradient_rect(c, (0, 0, W, sky_h + 40), [((176, 214, 160), 0.0), ((150, 196, 130), 1.0)])
        rng = np.random.default_rng(seed)
        for i in range(30):
            x = rng.uniform(0, W)
            c.drawCircle(x, sky_h + rng.uniform(-30, 10), rng.uniform(30, 80), paint((110, 170, 100), 0.35, blur=20))
    sc = mix(SOIL, (64, 44, 34), wet)
    gradient_rect(c, (0, sky_h, W, H), [(shade(sc, 0.9), 0.0), (sc, 0.5), (shade(sc, 1.08), 1.0)])
    rng = np.random.default_rng(seed)
    for i in range(700):
        y = sky_h + (H - sky_h) * rng.random() ** 0.8
        r = (2 + 10 * rng.random()) * (0.4 + (y - sky_h) / (H - sky_h + 1))
        cc = shade(sc, rng.uniform(0.75, 1.25))
        c.drawCircle(rng.uniform(0, W), y, r, paint(cc, 0.9))
        if rng.random() < 0.3:
            c.drawCircle(rng.uniform(0, W), y, r * 0.4, paint(shade(sc, 1.4), 0.5))
    if hole > 0:
        c.drawOval(skia.Rect(W / 2 - 130, 600 - 50, W / 2 + 130, 600 + 50), paint((36, 24, 18), hole))
        c.drawOval(skia.Rect(W / 2 - 150, 600 - 66, W / 2 + 150, 600 + 66), paint(shade(sc, 1.2), 0.5 * hole, style="stroke", width=16))


def finger(c, base, tip, w, skin, nail=True):
    D = Draw(c)
    pth, C = tube([base, ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2), tip], [w, w * 0.95, w * 0.85], n=16)
    D.shape(pth, skin, line=shade(skin, 0.6), lw=3, shadow=(-w * 0.15, -w * 0.1, shade(skin, 0.85), 8))
    if nail:
        d = np.array(tip) - np.array(base); d /= np.linalg.norm(d) + 1e-6
        nx, ny = tip[0] - d[0] * w * 0.35, tip[1] - d[1] * w * 0.35
        c.drawOval(skia.Rect(nx - w * 0.28, ny - w * 0.22, nx + w * 0.28, ny + w * 0.22), paint((255, 228, 220), 0.9))


def plant_seed(c, t, k, two_hands=False):
    """Пальчик Ясмины вдавливает семечко, потом ладошки укрывают землёй."""
    push = ease(k / 0.45)
    cover = ease((k - 0.5) / 0.45)
    soil_surface(c, hole=1.0 - cover)
    cx, cy = W / 2, 600
    if push < 1 or cover <= 0:
        seed_shape(c, cx, cy - 60 * (1 - push) + 10, 1.4, ang=10, t=t)
    if cover > 0:
        rng = np.random.default_rng(3)
        for i in range(int(90 * cover)):
            a, r = rng.uniform(0, 6.28), rng.uniform(0, 150)
            c.drawCircle(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.4, rng.uniform(5, 14), paint(shade(SOIL, rng.uniform(0.9, 1.2))))
    if cover <= 0.05:
        fy = cy - 520 + 470 * push
        finger(c, (cx + 420, fy - 380), (cx + 30, fy + 20), 120, yasmina.SKIN)
    else:
        sweep = math.sin(cover * math.pi * 2) * 120
        D = Draw(c)
        draw_hand(c, (cx + 520 + sweep, cy - 380), math.pi * 0.75, 420, HAND_PRESETS["relax"], yasmina.SKIN, shade(yasmina.SKIN, 0.6))
        if two_hands:
            draw_hand(c, (cx - 600 - sweep, cy - 420), math.pi * 0.28, 470, HAND_PRESETS["relax"], samir.SKIN, shade(samir.SKIN, 0.6))


def drops(c, t, t0, k):
    """Носик лейки сверху, капли падают на землю, круги и тёмное мокрое пятно."""
    soil_surface(c, wet=ease(k * 1.5) * 0.8)
    D = Draw(c)
    sx, sy = 1300, 170
    c.save(); c.translate(sx, sy); c.rotate(28); c.scale(1.8, 1.8)
    D.shape(poly_path([(-60, -30), (260, -50), (260, 50), (-60, 30)]), (90, 170, 214), line=(40, 90, 130), lw=3)
    D.ellipse(-70, 0, 26, 52, (110, 190, 230), line=(40, 90, 130), lw=3)
    for i in range(7):
        a = i * 0.9
        c.drawCircle(-74, math.sin(a) * 30, 5, paint((40, 90, 130)))
    c.restore()
    rng = np.random.default_rng(7)
    tt = t - t0
    for i in range(26):
        ph = rng.uniform(0, 1.2)
        life = (tt * 1.3 + ph) % 1.2
        x0 = sx - 80 + rng.uniform(-30, 30)
        x = x0 - life * 260
        y = sy + 40 + life * life * 900
        land = 560 + rng.uniform(-80, 120)
        if y < land:
            D.ellipse(x, y, 9, 15, (170, 216, 250), line=(90, 150, 210), lw=2, alpha=0.9)
        else:
            rr = (y - land) * 0.25
            if rr < 70:
                c.drawOval(skia.Rect(x - rr, land - rr * 0.3, x + rr, land + rr * 0.3), paint((190, 226, 250), max(0, 0.6 - rr / 120), style="stroke", width=3))


def root_section(c, t, k):
    """Разрез земли: над землёй — тёплое небо, под землёй — семечко пускает корешок вниз (в темноте)."""
    gy = 330
    gradient_rect(c, (0, 0, W, gy), [((255, 214, 170), 0.0), ((255, 190, 140), 1.0)])
    for i, x in enumerate(range(0, W, 26)):
        Draw(c).tapered([(x, gy + 4), (x + 6 * math.sin(t + i), gy - 30 - 14 * (i % 3))], 6, 1, (110, 160, 90))
    gradient_rect(c, (0, gy, W, H), [((104, 70, 50), 0.0), ((70, 46, 36), 0.5), ((44, 30, 26), 1.0)])
    rng = np.random.default_rng(2)
    for i in range(240):
        y = rng.uniform(gy, H)
        c.drawCircle(rng.uniform(0, W), y, rng.uniform(2, 9), paint((150, 110, 80), 0.25))
    for i in range(7):
        x, y = rng.uniform(0, W), rng.uniform(gy + 200, H - 60)
        Draw(c).ellipse(x, y, rng.uniform(20, 40), rng.uniform(12, 22), (130, 120, 116), line=(80, 70, 66), lw=2)
    sx, sy = W / 2, gy + 160
    g = ease(k)
    radial(c, sx, sy + 200 * g, 260, [((255, 236, 180), 0.22 * g, 0.0), ((255, 236, 180), 0.0, 1.0)])
    D = Draw(c)
    L = 520 * g
    pts = [(sx, sy + 30)] + [(sx + 24 * math.sin(q * 3.1 + 0.4), sy + 30 + L * q) for q in (0.25, 0.5, 0.75, 1.0)]
    if g > 0.02:
        D.tapered(pts, 14, 2, (250, 244, 226))
        for q in (0.35, 0.55, 0.75):
            if g > q:
                bx, by = sx + 24 * math.sin(q * 3.1 + 0.4), sy + 30 + L * q
                for side in (-1, 1):
                    D.tapered([(bx, by), (bx + side * 70 * (g - q), by + 50 * (g - q))], 5, 1, (240, 232, 214))
    seed_shape(c, sx, sy, 1.3, ang=180, t=t)


def sprout(c, t, k):
    soil_surface(c, wet=0.3, horizon=0.36)
    D = Draw(c)
    g = ease(k)
    cx, cy = W / 2, 690
    h = 330 * g
    tip = (cx + 10 * math.sin(t * 1.3), cy - h)
    D.tapered([(cx, cy), (cx + 6, cy - h * 0.5), tip], 26, 16, (110, 178, 90))
    leaf_k = ease((k - 0.45) / 0.5)
    for side in (-1, 1):
        L = 190 * leaf_k
        if L > 3:
            lf = smooth_path([tip, (tip[0] + side * L * 0.5, tip[1] - L * 0.45), (tip[0] + side * L, tip[1] - L * 0.08), (tip[0] + side * L * 0.45, tip[1] + L * 0.18)], tension=0.6)
            D.shape(lf, (130, 200, 100), line=(60, 120, 60), lw=3, shadow=(-10, -8, (100, 170, 80), 8), light=(6, 6, (220, 255, 200), 6))
            D.stroke([tip, (tip[0] + side * L * 0.85, tip[1] - L * 0.08)], (80, 150, 70), 2.5)
    for i in range(4):  # крошки земли, сдвинутые ростком
        a = -math.pi / 2 + (i - 1.5) * 0.7
        c.drawCircle(cx + math.cos(a) * 60 * g, cy + 6 - abs(math.sin(a)) * 12 * g, 12, paint(shade(SOIL, 1.1)))
    if k > 0.5:
        for i in range(12):
            a = t * 1.2 + i * 0.52
            r = 230 + 30 * math.sin(t * 2 + i)
            c.drawCircle(cx + math.cos(a) * r, cy - 220 + math.sin(a) * r * 0.5, 4 + 4 * abs(math.sin(t * 5 + i)), paint((255, 252, 220), 0.7 * leaf_k))


def ribbon_stem(c, t, k, wind=0.6):
    bokeh(c, (150, 160, 184), [(200, 210, 230), (170, 190, 170), (220, 220, 240)], 6, t)
    D = Draw(c)
    sway = math.sin(t * 2.3) * 18 * wind
    D.shape(poly_path([(1100, H), (1124, H), (1124, -10), (1100, -10)]), (186, 140, 90), line=(120, 84, 56), lw=3)
    stem = [(880, H + 20), (900 + sway * 0.4, 600), (920 + sway, -20)]
    D.tapered(stem, 70, 50, (96, 160, 80))
    D.tapered([(p[0] + 18, p[1]) for p in stem], 10, 8, (140, 200, 110), alpha=0.6)
    for y, side in ((800, -1), (420, 1), (150, -1)):
        bx = 900 + sway * (1 - y / H)
        lf = smooth_path([(bx, y), (bx + side * 200, y - 120), (bx + side * 330, y - 20), (bx + side * 160, y + 60)], tension=0.6)
        D.shape(lf, (104, 172, 86), line=(56, 110, 56), lw=3)
    by = 560
    bx = (920 + sway * 0.7 + 1112) / 2
    D.tapered([(905 + sway * 0.6, by), (1112, by)], 24, 24, (120, 206, 180))
    bk = ease((k - 0.35) / 0.5)
    for side in (-1, 1):
        if bk > 0.01:
            loop = smooth_path([(bx, by), (bx + side * 130 * bk, by - 90 * bk), (bx + side * 150 * bk, by + 30 * bk)], tension=0.6)
            D.shape(loop, (120, 206, 180), line=(60, 130, 110), lw=3, shadow=(-10, -6, (96, 180, 156), 6))
            D.tapered([(bx, by + 10), (bx + side * 60 * bk, by + 170 * bk + math.sin(t * 6 + side) * 10 * wind)], 26, 10, (120, 206, 180))
    c.drawCircle(bx, by, 22, paint((96, 186, 160)))
    if k < 0.6:  # мамины руки затягивают узел
        pull = math.sin(k * math.pi * 3) * 30
        for side in (-1, 1):
            ang = math.atan2(-300, -side * 420)
            draw_hand(c, (bx + side * (430 + pull), by + 330), ang, 330, HAND_PRESETS["pinch"], leyla.SKIN, shade(leyla.SKIN, 0.6))
            sleeve_cuff(c, bx + side * (470 + pull), by + 380, 200, -side * 0.95, leyla.CARDI)


def schedule(c, t, k, checks, hand=False, drift=None):
    """Расписание полива на холодильнике: 7 клеток с капелькой, галочки по дням (без текста).
    drift 0..1 — медленный наезд камеры и палец Самира, который ведёт по клеточкам."""
    gradient_rect(c, (0, 0, W, H), [((250, 246, 236), 0.0), ((240, 234, 222), 1.0)])
    D = Draw(c)
    dz = drift if drift is not None else k
    c.save(); c.translate(W / 2, H / 2 + 20); c.scale(1.0 + 0.07 * dz, 1.0 + 0.07 * dz); c.rotate(-2.5)
    sheet = skia.Rect(-720, -400, 720, 420)
    c.drawRect(sheet.makeOffset(14, 18), paint((60, 50, 50), 0.15, blur=16))
    c.drawRect(sheet, paint((255, 255, 252)))
    # солнце и подсолнух вверху — нарисовано Самиром
    c.drawCircle(-560, -280, 60, paint((255, 206, 70)))
    for q in range(10):
        a = q * 0.628
        D.stroke([(-560 + math.cos(a) * 75, -280 + math.sin(a) * 75), (-560 + math.cos(a) * 100, -280 + math.sin(a) * 100)], (255, 180, 40), 6)
    for q in range(12):
        a = q * 0.523
        D.ellipse(520 + math.cos(a) * 60, -270 + math.sin(a) * 60, 30, 14, (255, 200, 50), rot=a)
    c.drawCircle(520, -270, 40, paint((130, 84, 50)))
    D.stroke([(-300, -250), (300, -250)], (120, 170, 220), 8)
    for i in range(7):
        x0 = -660 + i * 190
        r = skia.Rect(x0, -120, x0 + 170, 300)
        c.drawRoundRect(r, 14, 14, paint((120, 170, 220), style="stroke", width=6))
        D.ellipse(x0 + 85, 10, 26, 36, (140, 196, 240), line=(80, 130, 190), lw=4)   # капля
        c.drawCircle(x0 + 85, -60, 22, paint((255, 214, 90), 0.9))                     # солнышко = утро
        if i < checks or (i == checks and k > 0.2):
            g = 1.0 if i < checks else ease((k - 0.2) / 0.6)
            pts = [(x0 + 40, 190), (x0 + 75, 240), (x0 + 140, 140)]
            seg = pts[:2] if g < 0.5 else pts
            if g < 0.5:
                seg = [pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * g * 2, pts[0][1] + (pts[1][1] - pts[0][1]) * g * 2)]
            else:
                q = (g - 0.5) * 2
                seg = [pts[0], pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * q, pts[1][1] + (pts[2][1] - pts[1][1]) * q)]
            D.stroke(seg, (70, 170, 90), 16, smooth=False)
    c.drawCircle(0, -360, 36, paint((230, 80, 80)))
    c.drawCircle(-10, -370, 10, paint((255, 255, 255), 0.6))
    c.restore()
    if hand and drift is not None:
        g = ease(min(1.0, drift * 1.15))
        fx = W / 2 - 560 + 1050 * g + 20 * math.sin(t * 6)
        fy = H / 2 + 330 + 30 * math.sin(drift * math.pi * 7) ** 2
        draw_hand(c, (fx + 40, fy + 330), -math.pi / 2 - 0.15, 360, HAND_PRESETS["point"], samir.SKIN, shade(samir.SKIN, 0.6))
        sleeve_cuff(c, fx + 45, fy + 380, 190, -0.15, samir.SWEAT)


def magnifier_eye(c, t, k, ch_pose):
    """Самир смотрит через лупу — глаз огромный (смешно)."""
    bokeh(c, (246, 228, 204), [(255, 250, 230), (220, 236, 220), (250, 210, 170)], 8, t)
    ch = Character(samir.DESIGN)
    p = dict(ch_pose); p.update(x=W / 2 - 40, y=0, u=900)
    J = ch.skeleton(p)
    p["y"] = H * 0.52 - J["head"][1] * p["u"]
    ch.draw(c, p)
    R = samir.DESIGN.head_r * p["u"]
    hx, hy = p["x"] + J["head"][0] * p["u"] * p.get("face", 1), p["y"] + J["head"][1] * p["u"]
    from face import feat_x
    yaw = p.get("head_yaw", 0.45)
    exl, _ = feat_x(samir.DESIGN.face.eye_sep, yaw, R)
    ex, ey = hx + exl * p.get("face", 1), hy + R * samir.DESIGN.face.eye_y
    lr = 260 * ease(k * 2)
    if lr > 5:
        c.save()
        circ = skia.Path(); circ.addCircle(ex, ey, lr)
        c.clipPath(circ, skia.ClipOp.kIntersect, True)
        c.translate(ex, ey); c.scale(1.8, 1.8); c.translate(-ex, -ey)
        bokeh(c, (246, 228, 204), [(255, 250, 230)], 8, t)
        ch.draw(c, p)
        c.restore()
        c.drawCircle(ex, ey, lr, paint((200, 230, 245), 0.15))
        c.drawCircle(ex, ey, lr, paint((60, 60, 70), style="stroke", width=34))
        D = Draw(c)
        D.tapered([(ex - lr * 0.6, ey - lr * 0.4), (ex - lr * 0.3, ey - lr * 0.7)], 18, 6, (255, 255, 255), alpha=0.7)
        D.shape(poly_path([(ex + lr * 0.6, ey + lr * 0.75), (ex + lr * 0.78, ey + lr * 0.6), (ex + lr * 1.4, ey + lr * 1.4), (ex + lr * 1.2, ey + lr * 1.6)]),
                (120, 76, 50), line=(70, 44, 30), lw=4)
