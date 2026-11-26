"""Интерьеры семейного дома: прихожая (с видом в гостиную через арку и в кухню), кухня, детская.
Каждая локация: render_layers(preset) -> {"main", "fg"}; мир WW×WH, пол — от FLOOR_Y вниз.
Точка схода перспективы — по центру, чуть выше уровня глаз ребёнка.
"""
import math
import numpy as np
import skia
from canvas import paint, smooth_path, poly_path, Draw, shade, mix, gradient_rect, radial, ellipse_pts, col
from home_common import (LIGHT, lit, box, contact, planks, wall, window, plant_pot, frame_pic, books, cushion, rug,
                         sunbeam, lamp_glow, grain)

WW, WH = 2600, 1200
FLOOR_Y = 780
PARALLAX = dict(main=1.0, fg=1.2)


def ceiling(c, P, color=(250, 244, 234), y1=110):
    gradient_rect(c, (0, 0, WW, y1), [(lit(shade(color, 0.9), P), 0.0), (lit(color, P), 1.0)])
    c.drawRect(skia.Rect(0, y1 - 10, WW, y1), paint(lit((236, 226, 212), P)))


def pendant(c, x, P, k=1.0, color=(240, 200, 150)):
    D = Draw(c)
    D.stroke([(x, 0), (x, 150)], lit((90, 80, 80), P), 2)
    shade_p = smooth_path([(x - 70, 210), (x - 40, 150), (x + 40, 150), (x + 70, 210)], tension=0.3)
    D.shape(shade_p, lit(color, P), line=lit(shade(color, 0.6), P), lw=2)
    c.drawOval(skia.Rect(x - 28, 200, x + 28, 218), paint((255, 236, 190), 0.9))
    if P["win"] > 0.3 or k > 1:
        lamp_glow(c, x, 230, 380, P, max(P["win"], 0.4) * k)


def coat(c, x, y, color, P, h=170, w=80):
    D = Draw(c)
    pth = smooth_path([(x, y), (x + w * 0.45, y + 20), (x + w * 0.55, y + h), (x - w * 0.55, y + h), (x - w * 0.45, y + 20)], tension=0.4)
    D.shape(pth, lit(color, P), line=lit(shade(color, 0.6), P), lw=2, shadow=(-12, -6, lit(shade(color, 0.82), P), 6))
    D.stroke([(x, y + 22), (x, y + h - 6)], lit(shade(color, 0.7), P), 2, alpha=0.6)
    c.drawCircle(x, y - 4, 7, paint(lit((200, 170, 110), P)))


def shoe_pair(c, x, y, color, P, s=1.0):
    for dx in (0, 34 * s):
        pth = smooth_path([(x + dx, y), (x + dx, y - 16 * s), (x + dx + 20 * s, y - 20 * s), (x + dx + 40 * s, y - 8 * s), (x + dx + 40 * s, y)], tension=0.4)
        Draw(c).shape(pth, lit(color, P), line=lit(shade(color, 0.55), P), lw=1.6)


def living_room_view(c, P, x0, x1, y0, y1):
    """Гостиная за аркой: окно с дневным светом, диван с подушками, книжная полка, растение, ковёр."""
    c.save(); c.clipRect(skia.Rect(x0, y0, x1, y1))
    k = 0.86
    gradient_rect(c, (x0, y0, x1, y1), [(lit((236, 214, 196), P, k), 0.0), (lit((226, 204, 186), P, k), 1.0)])
    fy = y1 - 60
    gradient_rect(c, (x0, fy, x1, y1), [(lit((196, 150, 106), P, k), 0.0), (lit((186, 140, 98), P, k), 1.0)])
    wx0, wx1 = x0 + (x1 - x0) * 0.52, x0 + (x1 - x0) * 0.88
    window(c, wx0, y0 + 90, wx1, fy - 160, P, curtain=(170, 200, 190), sill_plants=False, open_curtains=0.7, seed=3)
    # диван
    sx0, sx1 = x0 + 40, x0 + (x1 - x0) * 0.62
    box(c, sx0, fy - 150, sx1, fy - 60, (130, 160, 176), P, r=18, k=k)
    box(c, sx0 - 10, fy - 90, sx1 + 10, fy - 20, (140, 172, 188), P, r=14, k=k)
    for i, colr in enumerate(((240, 196, 120), (240, 170, 160), (190, 220, 200))):
        cushion(c, sx0 + 70 + i * 110, fy - 120, 90, 70, colr, P, rot=(i - 1) * 8, pattern="dots" if i == 1 else None)
    for lx in (sx0 + 10, sx1 - 24):
        c.drawRect(skia.Rect(lx, fy - 20, lx + 14, fy), paint(lit((110, 80, 60), P, k)))
    # полка с книгами
    bx = x1 - 120
    box(c, bx, y0 + 140, bx + 110, fy, (190, 140, 96), P, r=3, k=k)
    for j in range(4):
        yy = y0 + 200 + j * 90
        books(c, bx + 8, yy, 94, 60, P, seed=j + 4)
        c.drawRect(skia.Rect(bx + 4, yy, bx + 106, yy + 8), paint(lit((160, 116, 80), P, k)))
    plant_pot(c, wx1 + 30 if wx1 + 60 < bx else wx0 - 40, fy - 4, 0.8, P, kind="big", seed=8)
    rug(c, (x0 + x1) / 2, fy + 30, (x1 - x0) * 0.35, 26, P, color=(200, 140, 120))
    c.drawRect(skia.Rect(x0, y0, x1, y1), paint((40, 30, 40), 0.06))
    c.restore()


def _hallway(P):
    s = skia.Surface(WW, WH); c = s.getCanvas()
    D = Draw(c)
    ceiling(c, P)
    wall(c, 0, 110, WW, FLOOR_Y, P, (248, 228, 206), wainscot=(214, 190, 160), wy=560, pattern="dots")
    planks(c, 0, FLOOR_Y, WW, WH, P, base=(206, 156, 108), vp=(1300, 300))
    # входная дверь
    box(c, 210, 300, 510, FLOOR_Y, (156, 104, 74), P, r=6)
    c.drawRoundRect(skia.Rect(260, 350, 460, 470), 60, 60, paint(lit((206, 230, 240), P)))
    c.drawRoundRect(skia.Rect(260, 350, 460, 470), 60, 60, paint(lit((120, 80, 60), P), style="stroke", width=5))
    for yy in (520, 640):
        c.drawRoundRect(skia.Rect(250, yy, 470, yy + 100), 6, 6, paint(lit((136, 90, 64), P), style="stroke", width=3))
    c.drawCircle(480, 560, 9, paint(lit((230, 190, 90), P)))
    rug(c, 360, FLOOR_Y + 60, 200, 30, P, color=(150, 120, 100), border=(200, 176, 140))
    # вешалка и куртки
    box(c, 580, 360, 940, 384, (176, 126, 86), P, r=4)
    for x, colr, h in ((630, (226, 140, 120), 210), (720, (240, 200, 110), 140), (800, (110, 170, 200), 150), (880, (170, 160, 210), 120)):
        coat(c, x, 384, colr, P, h=h, w=70 if h < 160 else 86)
    # скамейка для обуви
    box(c, 580, 690, 940, 714, (186, 134, 92), P, r=4)
    for lx in (600, 900):
        c.drawRect(skia.Rect(lx, 714, lx + 18, FLOOR_Y), paint(lit((150, 104, 70), P)))
    shoe_pair(c, 610, FLOOR_Y - 2, (240, 140, 66), P, 0.9)
    shoe_pair(c, 720, FLOOR_Y - 2, (108, 196, 170), P, 0.75)
    shoe_pair(c, 820, FLOOR_Y - 2, (150, 98, 70), P, 1.0)
    # зеркало
    c.drawOval(skia.Rect(640, 160, 880, 330), paint(lit((196, 150, 100), P)))
    c.drawOval(skia.Rect(656, 176, 864, 314), paint(lit((214, 232, 240), P)))
    D.stroke([(700, 210), (760, 190)], (255, 255, 255), 6, alpha=0.6)
    # арка в гостиную
    ax0, ax1 = 1060, 1680
    acx, arx = (ax0 + ax1) / 2, (ax1 - ax0) / 2
    arch = poly_path([(ax0, FLOOR_Y)] + [(acx - arx * math.cos(a), 360 - 160 * math.sin(a)) for a in np.linspace(0, math.pi, 40)] + [(ax1, FLOOR_Y)])
    c.save(); c.clipPath(arch, skia.ClipOp.kIntersect, True)
    living_room_view(c, P, ax0, ax1, 180, FLOOR_Y)
    c.restore()
    c.drawPath(arch, paint(lit((240, 232, 220), P), style="stroke", width=26))
    c.drawPath(arch, paint(lit((200, 180, 160), P), style="stroke", width=3))
    sunbeam(c, ax0 + 340, 300, ax0 + 560, 600, P, FLOOR_Y, alpha=P["beam"] * 0.7)
    # дверь в кухню — тёплый свет
    kx0, kx1 = 2000, 2300
    gradient_rect(c, (kx0, 300, kx1, FLOOR_Y), [(lit((255, 236, 200), P), 0.0), (lit((246, 222, 190), P), 1.0)])
    c.drawRect(skia.Rect(kx0, 640, kx1, FLOOR_Y), paint(lit((220, 210, 190), P)))
    box(c, kx0 + 120, 420, kx1 + 40, 640, (180, 210, 190), P, r=4, k=0.95)  # шкафчик кухни вдали
    c.drawRect(skia.Rect(kx0 - 16, 284, kx1 + 16, 300), paint(lit((240, 232, 220), P)))
    c.drawRect(skia.Rect(kx0 - 16, 300, kx0, FLOOR_Y), paint(lit((240, 232, 220), P)))
    c.drawRect(skia.Rect(kx1, 300, kx1 + 16, FLOOR_Y), paint(lit((240, 232, 220), P)))
    p = paint((255, 236, 200), 0.22, blur=30); p.setBlendMode(skia.BlendMode.kScreen)
    c.drawPath(poly_path([(kx0, FLOOR_Y), (kx1, FLOOR_Y), (kx1 + 160, WH), (kx0 - 60, WH)]), p)
    # рисунки детей и часы
    frame_pic(c, 1760, 330, 150, 110, P, "sun")
    frame_pic(c, 1790, 470, 110, 80, P, "flower")
    frame_pic(c, 2380, 300, 160, 120, P, "pattern")
    c.drawCircle(2460, 520, 54, paint(lit((250, 248, 240), P)))
    c.drawCircle(2460, 520, 54, paint(lit((170, 120, 90), P), style="stroke", width=6))
    D.stroke([(2460, 520), (2460, 484)], lit((70, 60, 60), P), 4)
    D.stroke([(2460, 520), (2486, 532)], lit((70, 60, 60), P), 4)
    plant_pot(c, 2420, FLOOR_Y + 30, 1.1, P, kind="big", seed=4)
    pendant(c, 760, P)
    pendant(c, 1900, P)
    grain(c, WW, WH, seed=5, strength=5)
    return s.makeImageSnapshot()


def _kitchen(P):
    s = skia.Surface(WW, WH); c = s.getCanvas()
    D = Draw(c)
    ceiling(c, P)
    wall(c, 0, 110, WW, FLOOR_Y, P, (226, 238, 226), pattern="stripes", wy=FLOOR_Y)
    # пол — тёплая плитка
    gradient_rect(c, (0, FLOOR_Y, WW, WH), [(lit((222, 196, 170), P), 0.0), (lit((232, 208, 182), P), 1.0)])
    for i in range(-30, 60):
        xb = i * 90
        D.stroke([(1300 + (xb - 1300) * 0.35, FLOOR_Y), (xb, WH)], lit((200, 172, 148), P), 1.4, alpha=0.7)
    for yy in (800, 828, 864, 910, 968, 1040, 1130):
        D.stroke([(0, yy), (WW, yy)], lit((200, 172, 148), P), 1.4, alpha=0.7)
    gradient_rect(c, (0, FLOOR_Y, WW, FLOOR_Y + 40), [((40, 26, 30, 70), 0.0), ((40, 26, 30, 0), 1.0)])
    # фартук из плитки
    c.drawRect(skia.Rect(120, 500, 1650, 620), paint(lit((246, 246, 240), P)))
    for xx in range(120, 1650, 40):
        D.stroke([(xx, 500), (xx, 620)], lit((200, 210, 214), P), 1.2)
    for yy in range(500, 620, 30):
        D.stroke([(120, yy), (1650, yy)], lit((200, 210, 214), P), 1.2)
    for xx in range(160, 1650, 160):
        c.drawCircle(xx, 560, 8, paint(lit((110, 160, 190), P), 0.6))
    # нижние шкафы и столешница
    for x in range(120, 1650, 190):
        box(c, x, 640, x + 186, FLOOR_Y - 10, (170, 204, 182), P, r=4)
        c.drawRoundRect(skia.Rect(x + 80, 660, x + 106, 668), 3, 3, paint(lit((200, 170, 110), P)))
    box(c, 100, 610, 1670, 642, (232, 214, 190), P, r=4)
    # верхние шкафы
    for x in (120, 330, 1450):
        box(c, x, 180, x + 200, 420, (176, 208, 186), P, r=4)
        c.drawRoundRect(skia.Rect(x + 90, 390, x + 110, 398), 3, 3, paint(lit((200, 170, 110), P)))
    # полка с банками
    box(c, 560, 420, 860, 436, (186, 134, 92), P, r=3)
    for i, cc in enumerate(((240, 200, 120), (200, 120, 100), (150, 190, 150), (240, 230, 210))):
        c.drawRoundRect(skia.Rect(580 + i * 70, 360, 630 + i * 70, 420), 8, 8, paint(lit(cc, P)))
        c.drawRect(skia.Rect(580 + i * 70, 352, 630 + i * 70, 364), paint(lit((170, 130, 90), P)))
    # окно над мойкой
    window(c, 960, 240, 1380, 520, P, curtain=(250, 214, 150), sill_plants=True, open_curtains=0.8, seed=6)
    c.drawRoundRect(skia.Rect(1060, 612, 1280, 630), 8, 8, paint(lit((200, 206, 210), P)))
    D.stroke([(1170, 612), (1170, 560), (1200, 545), (1215, 560)], lit((180, 186, 196), P), 8)
    # чайник и миска с фруктами
    D.ellipse(520, 580, 60, 46, lit((240, 120, 100), P), line=lit((150, 70, 60), P), lw=2)
    D.stroke([(570, 570), (610, 545)], lit((240, 120, 100), P), 10)
    c.drawRoundRect(skia.Rect(500, 522, 540, 534), 4, 4, paint(lit((150, 70, 60), P)))
    D.ellipse(1520, 600, 90, 24, lit((246, 240, 230), P), line=lit((180, 170, 160), P), lw=2)
    for i, (dx, cc) in enumerate(((-40, (230, 80, 70)), (0, (250, 200, 70)), (40, (120, 190, 90)), (-18, (240, 150, 60)))):
        c.drawCircle(1520 + dx, 584 - (i == 3) * 18, 24, paint(lit(cc, P)))
    # холодильник
    box(c, 1760, 250, 2040, FLOOR_Y, (250, 244, 232), P, r=18)
    D.stroke([(1764, 470), (2036, 470)], lit((210, 200, 190), P), 3)
    for yy in (330, 540):
        c.drawRoundRect(skia.Rect(1780, yy, 1792, yy + 90), 4, 4, paint(lit((190, 180, 170), P)))
    frame_pic(c, 1950, 300, 70, 60, P, "family")
    for i, (mx, my, cc) in enumerate(((1830, 290, (240, 100, 100)), (2000, 520, (100, 170, 230)), (1860, 650, (250, 200, 70)))):
        c.drawCircle(mx, my, 11, paint(lit(cc, P)))
    # стол со скатертью и стульями
    tx0, tx1, ty = 2130, 2540, 860
    for cx in (2180, 2490):
        box(c, cx - 50, ty - 170, cx + 50, ty - 40, (186, 134, 92), P, r=10)
        for lx in (-44, 32):
            c.drawRect(skia.Rect(cx + lx, ty - 40, cx + lx + 12, ty + 110), paint(lit((150, 104, 70), P)))
    tbl = smooth_path([(tx0, ty - 40), (tx1, ty - 40), (tx1 + 20, ty + 50), (tx0 - 20, ty + 50)], tension=0.1)
    D.shape(tbl, lit((250, 236, 222), P), line=lit((200, 160, 150), P), lw=2, shadow=(0, -16, lit((230, 210, 196), P), 6))
    for xx in range(tx0, tx1, 40):
        c.drawRect(skia.Rect(xx, ty - 40, xx + 20, ty + 50), paint(lit((240, 170, 160), P), 0.35))
    for lx in (tx0 + 20, tx1 - 40):
        c.drawRect(skia.Rect(lx, ty + 50, lx + 20, ty + 200), paint(lit((150, 104, 70), P)))
    D.ellipse(2330, ty - 46, 46, 14, lit((246, 240, 230), P), line=lit((180, 170, 160), P), lw=2)
    for k in range(5):
        c.drawCircle(2310 + k * 10, ty - 56, 10, paint(lit((210, 160, 100), P)))   # печенье
    sunbeam(c, 960, 240, 1380, 520, P, FLOOR_Y)
    pendant(c, 2370, P, color=(250, 214, 150))
    grain(c, WW, WH, seed=6, strength=5)
    return s.makeImageSnapshot()


def _yard_view(c, r, preset):
    """Вид из окна детской во двор (мелко): небо, сад, грядка с подсолнухом."""
    import loc_yard
    x0, y0, x1, y1 = r
    L = _yard_cache(preset)
    sc = (x1 - x0) / 1500
    c.save(); c.translate(x0, y0); c.scale(sc, sc); c.translate(-900, -360)
    for k in ("far", "mid", "main"):
        c.drawImage(L[k], 0, 0)
    c.restore()


_YC = {}


def _yard_cache(preset):
    import loc_yard
    if preset not in _YC:
        _YC[preset] = loc_yard.render_layers(preset)
    return _YC[preset]


def _kidsroom(P, preset):
    s = skia.Surface(WW, WH); c = s.getCanvas()
    D = Draw(c)
    ceiling(c, P, color=(244, 240, 250))
    wall(c, 0, 110, WW, FLOOR_Y, P, (222, 224, 244), pattern="dots", wy=FLOOR_Y)
    planks(c, 0, FLOOR_Y, WW, WH, P, base=(214, 170, 124), vp=(1300, 300))
    # гирлянда-звёздочки
    for i, x in enumerate(range(140, 2500, 110)):
        y = 170 + 30 * math.sin(i * 0.7) ** 2
        c.drawCircle(x, y, 8, paint((255, 230, 150), 0.6 + 0.4 * P["win"]))
        if P["win"] > 0.3:
            lamp_glow(c, x, y, 40, P, P["win"] * 0.8)
    window(c, 1000, 250, 1600, 640, P, view=lambda cc, r: _yard_view(cc, r, preset), curtain=(186, 200, 236), sill_plants=True, open_curtains=0.85, seed=9)
    # кровать с одеялом, подушкой и зайкой
    box(c, 120, 520, 160, FLOOR_Y + 20, (210, 160, 120), P, r=6)
    box(c, 140, 650, 780, 760, (230, 214, 196), P, r=10)
    blanket = smooth_path([(200, 640), (780, 650), (800, 760), (760, 800), (190, 790)], tension=0.4)
    D.shape(blanket, lit((250, 196, 160), P), line=lit((190, 130, 110), P), lw=2, shadow=(-20, -10, lit((236, 176, 140), P), 8))
    for k in range(5):
        for j in range(3):
            c.drawCircle(260 + k * 110, 680 + j * 36, 9, paint(lit((255, 236, 210), P), 0.9))
    cushion(c, 230, 615, 150, 80, (255, 250, 244), P)
    bunny_x, bunny_y = 360, 615
    D.ellipse(bunny_x, bunny_y, 34, 30, lit((246, 240, 236), P), line=lit((180, 170, 170), P), lw=2)
    for dx in (-14, 14):
        D.ellipse(bunny_x + dx, bunny_y - 50, 9, 26, lit((246, 240, 236), P), line=lit((180, 170, 170), P), lw=2)
    c.drawCircle(bunny_x - 10, bunny_y - 4, 4, paint((50, 40, 50))); c.drawCircle(bunny_x + 10, bunny_y - 4, 4, paint((50, 40, 50)))
    # полка с книгами и игрушками
    box(c, 1900, 260, 2300, FLOOR_Y, (196, 150, 108), P, r=4)
    for j in range(4):
        yy = 340 + j * 110
        books(c, 1916, yy, 260 if j % 2 else 180, 80, P, seed=10 + j)
        c.drawRect(skia.Rect(1906, yy, 2294, yy + 10), paint(lit((166, 122, 86), P)))
    D.ellipse(2240, 425, 30, 30, lit((250, 150, 120), P))           # мячик
    c.drawRect(skia.Rect(2200, 520, 2270, 560), paint(lit((120, 180, 220), P)))  # кубики
    c.drawRect(skia.Rect(2215, 490, 2255, 520), paint(lit((250, 210, 90), P)))
    rug(c, 1300, 1000, 520, 90, P, color=(176, 200, 236), border=(250, 230, 200))
    frame_pic(c, 600, 300, 160, 120, P, "family")
    # ночник
    c.drawRoundRect(skia.Rect(830, 600, 900, 660), 20, 20, paint((255, 226, 170), 0.6 + 0.4 * P["win"]))
    if P["win"] > 0.3:
        lamp_glow(c, 865, 630, 260, P, P["win"])
    sunbeam(c, 1000, 250, 1600, 640, P, FLOOR_Y)
    grain(c, WW, WH, seed=7, strength=5)
    return s.makeImageSnapshot()


def _fg_interior(P, kind):
    s = skia.Surface(WW, WH); c = s.getCanvas(); c.clear(col((0, 0, 0), 0.0))
    if kind == "hallway":
        plant_pot(c, 90, WH + 40, 1.7, P, kind="big", seed=12)
    elif kind == "kitchen":
        pass
    elif kind == "kidsroom":
        pass
    return s.makeImageSnapshot()


def render_layers(loc, preset):
    P = LIGHT[preset]
    if loc == "hallway":
        main = _hallway(P)
    elif loc == "kitchen":
        main = _kitchen(P)
    elif loc == "kidsroom":
        main = _kidsroom(P, preset)
    else:
        raise ValueError(loc)
    return dict(main=main, fg=_fg_interior(P, loc))
