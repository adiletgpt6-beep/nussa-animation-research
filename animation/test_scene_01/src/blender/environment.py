"""Окружение: лестничная площадка многоэтажки (лифт «НЕ РАБОТАЕТ», дверь квартиры, окно, перила)
и реквизит: две сумки, мяч. Всё строится кодом; внешних ассетов нет."""
import bpy, bmesh, math
from mathutils import Vector, Matrix
from common import mat, new_mesh_obj, prim, torus, link

WALL_Y = 2.0


def box(name, x0, x1, y0, y1, z0, z1, material, bevel=0.0):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = new_mesh_obj(name, v, f, mats=[material], smooth=False)
    if bevel:
        m = ob.modifiers.new("Bev", "BEVEL"); m.width = bevel; m.segments = 2
    return ob


def text(name, body, size, loc, rot, material, extrude=0.0005):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.extrude = extrude
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        try:
            cu.font = bpy.data.fonts.load(f); break
        except Exception:
            pass
    ob = bpy.data.objects.new(name, cu); link(ob)
    ob.location = loc; ob.rotation_euler = rot
    cu.materials.append(material)
    return ob


def build_environment():
    W = WALL_Y
    # пол: плитка 30 см в шахматном порядке (геометрией — работает и в 2D, и в 3D)
    t1 = mat("tile_a", (0.62, 0.50, 0.38), rough=0.45, spec=0.4)
    t2 = mat("tile_b", (0.42, 0.24, 0.16), rough=0.45, spec=0.4)
    verts, faces, mi = [], [], []
    s = 0.3
    nx, ny = 30, 20
    x0, y0 = -4.5, -4.0
    for j in range(ny):
        for i in range(nx):
            b = len(verts)
            xa, ya = x0 + i * s, y0 + j * s
            verts += [(xa, ya, 0), (xa + s, ya, 0), (xa + s, ya + s, 0), (xa, ya + s, 0)]
            faces.append((b, b + 1, b + 2, b + 3)); mi.append((i + j) % 2)
    fl = new_mesh_obj("floor", verts, faces, mats=[t1, t2], smooth=False)
    for p, m in zip(fl.data.polygons, mi):
        p.material_index = m
    # задняя стена: низ — крашеная панель, верх — побелка, полоса
    paint = mat("wall_paint", (0.18, 0.36, 0.32), rough=0.5, spec=0.5)
    white = mat("wall_white", (0.80, 0.78, 0.70), rough=0.9)
    stripe = mat("wall_stripe", (0.08, 0.18, 0.15), rough=0.5)
    # проём окна x -0.55..0.35, z 1.0..2.3
    wx0, wx1, wz0, wz1 = -0.55, 0.35, 1.05, 2.3
    for nm, (xa, xb, za, zb, m) in {
        "wall_lo_l": (-4.5, wx0, 0, 1.25, paint), "wall_lo_r": (wx1, 4.5, 0, 1.25, paint), "wall_lo_m": (wx0, wx1, 0, wz0, paint),
        "wall_hi_l": (-4.5, wx0, 1.25, 3.2, white), "wall_hi_r": (wx1, 4.5, 1.25, 3.2, white), "wall_hi_m": (wx0, wx1, wz1, 3.2, white),
        "wall_win_m": (wx0, wx1, wz0, 1.25, paint)}.items():
        box(nm, xa, xb, W, W + 0.25, za, zb, m)
    box("stripe_l", -4.5, wx0, W - 0.006, W, 1.235, 1.265, stripe)
    box("stripe_r", wx1, 4.5, W - 0.006, W, 1.235, 1.265, stripe)
    # плинтус
    box("plinth", -4.5, 4.5, W - 0.02, W, 0, 0.08, stripe)
    # окно: рама, стекло-небо, подоконник, цветок
    frame = mat("win_frame", (0.85, 0.85, 0.82), rough=0.4)
    sky = mat("sky", (0.55, 0.75, 0.95), emit=2.2)
    box("sky_plane", wx0, wx1, W + 0.24, W + 0.25, wz0, wz1, sky)
    for nm, (xa, xb, za, zb) in {"fr_b": (wx0, wx1, wz0, wz0 + 0.05), "fr_t": (wx0, wx1, wz1 - 0.05, wz1),
                                  "fr_l": (wx0, wx0 + 0.05, wz0, wz1), "fr_r": (wx1 - 0.05, wx1, wz0, wz1),
                                  "fr_m": ((wx0 + wx1) / 2 - 0.025, (wx0 + wx1) / 2 + 0.025, wz0, wz1),
                                  "fr_h": (wx0, wx1, 1.85, 1.89)}.items():
        box(nm, xa, xb, W + 0.12, W + 0.16, za, zb, frame)
    box("sill", wx0 - 0.08, wx1 + 0.08, W - 0.12, W + 0.12, wz0 - 0.04, wz0, frame)
    pot = mat("pot", (0.55, 0.22, 0.10), rough=0.6)
    leaf = mat("leaf", (0.12, 0.40, 0.10), rough=0.6, sss=0.1)
    flower = mat("flower", (0.85, 0.12, 0.15), rough=0.5)
    p = prim("cyl", "pot", size=0.07, loc=(0.12, W - 0.02, wz0 + 0.07), material=pot, segments=20); p.scale = (1, 1, 0.14)
    for i in range(7):
        a = i * 2.4
        l = prim("sphere", f"leaf{i}", size=0.05, loc=(0.12 + 0.06 * math.cos(a), W - 0.02 + 0.05 * math.sin(a), wz0 + 0.17 + 0.02 * (i % 3)),
                 material=leaf, segments=12, rings=6)
        l.scale = (1.3, 0.8, 0.45); l.rotation_euler = (0.3, 0.2, a)
    for i in range(3):
        prim("sphere", f"flower{i}", size=0.025, loc=(0.12 + 0.04 * math.cos(i * 2.1), W - 0.03 + 0.03 * math.sin(i * 2.1), wz0 + 0.24),
             material=flower, segments=10, rings=6)
    # батарея под окном
    rad = mat("radiator", (0.75, 0.74, 0.70), rough=0.35)
    for i in range(10):
        x = wx0 + 0.06 + i * 0.08
        box(f"rad{i}", x, x + 0.06, W - 0.12, W - 0.02, 0.2, 0.85, rad, bevel=0.01)
    # лифт: рама, створки, кнопка, объявление
    steel = mat("steel", (0.55, 0.57, 0.58), rough=0.35, metal=0.7)
    steel_d = mat("steel_dark", (0.25, 0.26, 0.27), rough=0.4, metal=0.5)
    ex0, ex1 = 1.0, 2.1
    box("lift_frame_l", ex0 - 0.08, ex0, W - 0.04, W, 0, 2.2, steel_d)
    box("lift_frame_r", ex1, ex1 + 0.08, W - 0.04, W, 0, 2.2, steel_d)
    box("lift_frame_t", ex0 - 0.08, ex1 + 0.08, W - 0.04, W, 2.1, 2.2, steel_d)
    box("lift_door_l", ex0, (ex0 + ex1) / 2 - 0.005, W - 0.02, W, 0, 2.1, steel)
    box("lift_door_r", (ex0 + ex1) / 2 + 0.005, ex1, W - 0.02, W, 0, 2.1, steel)
    box("lift_panel", ex1 + 0.18, ex1 + 0.3, W - 0.03, W, 1.0, 1.25, steel_d)
    btn = mat("lift_button", (0.9, 0.3, 0.1), emit=0.5)
    prim("cyl", "lift_btn", size=0.022, loc=(ex1 + 0.24, W - 0.035, 1.12), rot=(math.radians(90), 0, 0), material=btn, segments=16).scale = (1, 1, 0.01)
    paper = mat("paper", (0.95, 0.94, 0.90), rough=0.9)
    ink = mat("ink_red", (0.55, 0.04, 0.03), rough=0.8)
    box("sign_paper", 1.28, 1.82, W - 0.026, W - 0.022, 1.32, 1.66, paper)
    text("sign_text1", "ЛИФТ", 0.085, (1.55, W - 0.028, 1.56), (math.radians(90), 0, 0), ink)
    text("sign_text2", "НЕ РАБОТАЕТ", 0.06, (1.55, W - 0.028, 1.42), (math.radians(90), 0, 0), ink)
    # дверь квартиры: обивка «ромбами», ручка, номер
    door = mat("door_leather", (0.32, 0.12, 0.06), rough=0.55, spec=0.5)
    brass = mat("brass", (0.75, 0.55, 0.2), rough=0.3, metal=0.9)
    dx0, dx1 = -2.4, -1.5
    box("door_frame", dx0 - 0.07, dx1 + 0.07, W - 0.03, W, 0, 2.12, stripe)
    box("door", dx0, dx1, W - 0.06, W - 0.03, 0, 2.05, door, bevel=0.01)
    for i in range(4):
        for j in range(8):
            prim("sphere", f"stud{i}_{j}", size=0.012, loc=(dx0 + 0.12 + i * 0.22, W - 0.065, 0.2 + j * 0.24), material=brass, segments=8, rings=4)
    prim("sphere", "door_knob", size=0.035, loc=(dx1 - 0.1, W - 0.1, 1.0), material=brass, segments=16, rings=8)
    box("door_num", dx0 + 0.36, dx0 + 0.54, W - 0.07, W - 0.06, 1.62, 1.74, brass)
    text("door_num_t", "14", 0.08, ((dx0 + dx1) / 2, W - 0.073, 1.68), (math.radians(90), 0, 0), mat("ink_dark", (0.05, 0.04, 0.03)))
    # перила лестницы слева (Амир прибегает снизу по лестнице)
    rail = mat("rail_wood", (0.35, 0.18, 0.08), rough=0.4)
    bar = mat("rail_bar", (0.12, 0.12, 0.13), rough=0.4, metal=0.6)
    for i in range(9):
        y = -2.4 + i * 0.4
        box(f"baluster{i}", -3.42, -3.40, y, y + 0.02, 0, 0.95, bar)
    r = prim("cyl", "handrail", size=0.03, loc=(-3.41, -0.8, 0.97), rot=(math.radians(90), 0, 0), material=rail, segments=12)
    r.scale = (1, 1, 3.4)
    # правая стена, потолок
    box("wall_right", 3.2, 3.45, -4.0, W + 0.25, 0, 3.2, white)
    box("wall_left", -4.7, -4.45, -4.0, W + 0.25, 0, 3.2, paint)
    box("ceiling", -4.5, 4.5, -4.0, W + 0.25, 3.0, 3.1, white)
    lamp = mat("lamp", (1.0, 0.92, 0.75), emit=6.0)
    prim("sphere", "lamp_bulb", size=0.1, loc=(0.3, 0.2, 2.9), material=lamp, segments=16, rings=8)


def build_props():
    P = {}
    # мяч: икосфера, «пятиугольники» тёмные — узнаваемый футбольный мяч
    bw = mat("ball_white", (0.92, 0.92, 0.90), rough=0.35)
    bb = mat("ball_black", (0.05, 0.05, 0.06), rough=0.35)
    me = bpy.data.meshes.new("ball")
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    ico = [v.co.copy() for v in bm.verts]
    bm.free()
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.105)
    bm.to_mesh(me); bm.free()
    ball = bpy.data.objects.new("ball", me); link(ball)
    me.materials.append(bw); me.materials.append(bb)
    for p in me.polygons:
        c = p.center.normalized()
        p.material_index = 1 if max(c.dot(v.normalized()) for v in ico) > 0.95 else 0
        p.use_smooth = True
    P["ball"] = ball
    # сумка 1: тканевая, зелёная; origin — в точке хвата ручек
    P["bag_a"] = make_bag("bag_a", mat("bag_green", (0.18, 0.32, 0.16), rough=0.9), handle=mat("bag_handle", (0.10, 0.12, 0.08), rough=0.8),
                          size=(0.30, 0.14, 0.28), contents="flour")
    # сумка 2: клетчатая «базарная»
    P["bag_b"] = make_bag("bag_b", mat("bag_check_a", (0.75, 0.10, 0.08), rough=0.7), handle=mat("bag_handle_b", (0.2, 0.08, 0.06), rough=0.7),
                          size=(0.34, 0.16, 0.30), contents="apples", check=mat("bag_check_b", (0.90, 0.88, 0.82), rough=0.7))
    return P


def make_bag(name, m, handle, size, contents, check=None):
    w, d, h = size
    root = bpy.data.objects.new(name, None); link(root)
    root.empty_display_size = 0.05
    hh = 0.16  # высота ручек над сумкой
    # корпус: куб с подразделением; клетка — материалами по граням
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=7, use_grid_fill=True)
    for v in bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * d * (1 - 0.25 * max(0, v.co.z)), v.co.z * h - h / 2 - hh))
    me = bpy.data.meshes.new(name + "_body"); bm.to_mesh(me); bm.free()
    body = bpy.data.objects.new(me.name, me); link(body)
    me.materials.append(m)
    if check:
        me.materials.append(check)
        for p in me.polygons:
            c = p.center
            p.material_index = (int((c.x + 1) / (w / 4)) + int((c.z + 2) / (h / 4)) + int((c.y + 1) / (d / 2))) % 2
    # верх открыт
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9 and f.calc_center_median().z > -hh - 0.01], context="FACES")
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    so = body.modifiers.new("Sol", "SOLIDIFY"); so.thickness = 0.006
    sub = body.modifiers.new("Sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
    body.parent = root
    for sgn in (1, -1):
        t = torus(f"{name}_handle{sgn}", w * 0.32, 0.009, loc=(0, sgn * d * 0.36, -hh), material=handle, seg=20, mseg=8, arc=math.pi)
        t.rotation_euler = (math.radians(90), 0, 0)
        t.scale = (1, hh / (w * 0.32), 1)
        t.parent = root
    if contents == "flour":
        fm = mat("flour_pack", (0.93, 0.91, 0.84), rough=0.8)
        fp = box(name + "_flour", -0.09, 0.03, -0.04, 0.04, -hh - 0.12, -hh + 0.07, fm)
        fp.parent = root
        lab = mat("flour_label", (0.15, 0.30, 0.65), rough=0.7)
        lb = box(name + "_flourlab", -0.085, 0.025, -0.0405, -0.040, -hh - 0.03, -hh + 0.03, lab); lb.parent = root
        br = mat("bread", (0.70, 0.42, 0.16), rough=0.6)
        bread = prim("sphere", name + "_bread", size=1.0, loc=(0.08, 0.0, -hh + 0.02), material=br, segments=20, rings=10)
        bread.scale = (0.035, 0.035, 0.16); bread.rotation_euler = (0, math.radians(18), 0); bread.parent = root
    else:
        ap = mat("apple", (0.75, 0.08, 0.06), rough=0.35)
        ag = mat("apple_g", (0.45, 0.65, 0.12), rough=0.35)
        for i, (x, y) in enumerate(((-0.08, 0.0), (0.0, 0.03), (0.08, -0.01), (0.04, -0.04))):
            a = prim("sphere", f"{name}_apple{i}", size=0.04, loc=(x, y, -hh + 0.0), material=ap if i % 2 else ag, segments=16, rings=8)
            a.parent = root
    return root
