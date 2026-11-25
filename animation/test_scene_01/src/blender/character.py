"""Процедурный временный персонаж: скелет (тело, пальцы, лицо), тело Skin-модификатором,
веса по расстоянию до костей, лицо (глаза, веки, брови, рот с формами для lip sync).

Персонажи — ВРЕМЕННЫЕ тестовые, созданы кодом (лицензия — наша), финальный дизайн не утверждён.
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from common import mat, new_mesh_obj, prim, torus, parent_to_bone, link

FINGERS = ("index", "middle", "ring")  # мультяшная кисть: большой + 3 пальца


def _v(*a):
    return Vector(a)


def build_skeleton(sp):
    """Позиции суставов (в пространстве арматуры, персонаж смотрит в -Y)."""
    J = {}
    hz = sp["leg"]
    J["pelvis"] = (_v(0, 0, hz - 0.03), _v(0, 0, hz + sp["torso"] * 0.30))
    J["spine"] = (J["pelvis"][1], _v(0, 0, hz + sp["torso"] * 0.62))
    J["chest"] = (J["spine"][1], _v(0, 0, hz + sp["torso"]))
    J["neck"] = (J["chest"][1], _v(0, 0, hz + sp["torso"] + sp["neck"]))
    hb = J["neck"][1]
    J["head"] = (hb, hb + _v(0, 0, sp["head_r"] * 1.7))
    shz = hz + sp["torso"] - sp["sh_drop"]
    a = math.radians(sp["arm_angle"])
    for s, side in ((1, "L"), (-1, "R")):
        c0, c1 = _v(s * 0.02, 0, shz), _v(s * sp["sh_w"], 0, shz)
        d = _v(s * math.cos(a), 0, -math.sin(a))
        el = c1 + d * sp["upper"] + _v(0, 0.012, 0)
        wr = el - _v(0, 0.012, 0) + d * sp["fore"]
        he = wr + d * sp["hand"]
        J["clav." + side] = (c0, c1)
        J["upperarm." + side] = (c1, el)
        J["forearm." + side] = (el, wr)
        J["hand." + side] = (wr, wr + d * sp["hand"] * 0.75)
        kn = wr + d * sp["hand"] * 0.75
        fw = sp["finger_gap"]
        for i, f in enumerate(FINGERS):
            off = _v(0, (i - 1) * fw, 0)
            L = sp["finger"] * (1.0 if f == "middle" else 0.9)
            p0 = kn + off
            p1 = p0 + d * L * 0.55
            p2 = p1 + d * L * 0.45
            J[f"{f}1.{side}"] = (p0, p1)
            J[f"{f}2.{side}"] = (p1, p2)
        tb = wr + d * sp["hand"] * 0.3 + _v(0, -sp["finger_gap"] * 1.4, 0)
        td = (d * 0.55 + _v(0, -0.8, 0)).normalized()
        t1 = tb + td * sp["finger"] * 0.45
        t2 = t1 + td * sp["finger"] * 0.4
        J["thumb1." + side] = (tb, t1)
        J["thumb2." + side] = (t1, t2)
        hip = _v(s * sp["leg_w"], 0, hz)
        knee = _v(s * sp["leg_w"], -0.012, hz - sp["thigh"])
        ank = _v(s * sp["leg_w"], 0, sp["ankle_h"])
        ball = _v(s * sp["leg_w"], -sp["foot"] * 0.68, 0.025)
        toe = _v(s * sp["leg_w"], -sp["foot"], 0.025)
        J["thigh." + side] = (hip, knee)
        J["shin." + side] = (knee, ank)
        J["foot." + side] = (ank, ball)
        J["toe." + side] = (ball, toe)
    return J


PARENT = {"spine": "pelvis", "chest": "spine", "neck": "chest", "head": "neck"}
for _s in "LR":
    PARENT.update({f"clav.{_s}": "chest", f"upperarm.{_s}": f"clav.{_s}", f"forearm.{_s}": f"upperarm.{_s}",
                   f"hand.{_s}": f"forearm.{_s}", f"thigh.{_s}": "pelvis", f"shin.{_s}": f"thigh.{_s}",
                   f"foot.{_s}": f"shin.{_s}", f"toe.{_s}": f"foot.{_s}", f"thumb1.{_s}": f"hand.{_s}",
                   f"thumb2.{_s}": f"thumb1.{_s}"})
    for _f in FINGERS:
        PARENT[f"{_f}1.{_s}"] = f"hand.{_s}"
        PARENT[f"{_f}2.{_s}"] = f"{_f}1.{_s}"


def make_armature(name, J, face_bones, extra_bones):
    arm_data = bpy.data.armatures.new(name + "_rig")
    arm = bpy.data.objects.new(name, arm_data)
    link(arm)
    arm_data.display_type = "STICK"
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for n, (h, t) in J.items():
        b = eb.new(n)
        b.head, b.tail = h, t
        b.align_roll(Vector((0, -1, 0)) if abs((t - h).normalized().y) < 0.9 else Vector((0, 0, 1)))
    for n, (h, t, parent) in list(face_bones.items()) + list(extra_bones.items()):
        b = eb.new(n)
        b.head, b.tail = h, t
        b.align_roll(Vector((0, 0, 1)))
        b.use_deform = False
    for n, b in eb.items():
        p = PARENT.get(n) or (face_bones.get(n) or extra_bones.get(n) or (None, None, None))[2]
        if p:
            b.parent = eb[p]
            if n in J and p in J and (J[p][1] - J[n][0]).length < 1e-4:
                b.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def body_mesh(name, sp, J, mats_fn):
    """Тело единым мешем через Skin-модификатор по графу суставов."""
    verts, edges, radii = [], [], []
    idx = {}

    def add(key, p, r):
        idx[key] = len(verts)
        verts.append(tuple(p))
        radii.append(r)
        return idx[key]

    R = sp["radii"]
    hz = sp["leg"]
    add("pelvis", J["pelvis"][0], R["pelvis"])
    add("spine", J["spine"][0], R["spine"])
    add("chest", J["chest"][0], R["chest"])
    add("clavroot", J["clav.L"][0] * 0 + Vector((0, 0, J["clav.L"][0].z)), R["clavroot"])
    add("neck", J["neck"][0] + Vector((0, 0, 0.01)), R["neck"])
    add("necktop", J["neck"][1] + Vector((0, 0, sp["head_r"] * 0.3)), R["neck"] * 0.9)
    for a, b in (("pelvis", "spine"), ("spine", "chest"), ("chest", "clavroot"), ("clavroot", "neck"), ("neck", "necktop")):
        edges.append((idx[a], idx[b]))
    for s in "LR":
        add("sh" + s, J["clav." + s][1], R["shoulder"])
        add("el" + s, J["forearm." + s][0], R["elbow"])
        add("wr" + s, J["hand." + s][0], R["wrist"])
        add("kn" + s, J["hand." + s][1], R["palm"])
        edges += [(idx["clavroot"], idx["sh" + s]), (idx["sh" + s], idx["el" + s]), (idx["el" + s], idx["wr" + s]),
                  (idx["wr" + s], idx["kn" + s])]
        for f in FINGERS:
            add(f + "1" + s, J[f"{f}1.{s}"][0], R["finger"] * 1.1)
            add(f + "2" + s, J[f"{f}2.{s}"][0], R["finger"])
            add(f + "3" + s, J[f"{f}2.{s}"][1], R["finger"] * 0.85)
            edges += [(idx["kn" + s], idx[f + "1" + s]), (idx[f + "1" + s], idx[f + "2" + s]), (idx[f + "2" + s], idx[f + "3" + s])]
        add("t1" + s, J["thumb1." + s][0], R["finger"] * 1.25)
        add("t2" + s, J["thumb2." + s][0], R["finger"] * 1.1)
        add("t3" + s, J["thumb2." + s][1], R["finger"] * 0.95)
        edges += [(idx["wr" + s], idx["t1" + s]), (idx["t1" + s], idx["t2" + s]), (idx["t2" + s], idx["t3" + s])]
        add("hip" + s, J["thigh." + s][0], R["hip"])
        add("knee" + s, J["shin." + s][0], R["knee"])
        add("ank" + s, J["foot." + s][0], R["ankle"])
        add("ball" + s, J["toe." + s][0], R["ball"])
        add("toe" + s, J["toe." + s][1], R["toe"])
        edges += [(idx["pelvis"], idx["hip" + s]), (idx["hip" + s], idx["knee" + s]), (idx["knee" + s], idx["ank" + s]),
                  (idx["ank" + s], idx["ball" + s]), (idx["ball" + s], idx["toe" + s])]
    ob = new_mesh_obj(name + "_body", verts, [], edges=edges, smooth=True)
    sk = ob.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.6
    for i, r in enumerate(radii):
        sv = ob.data.skin_vertices[0].data[i]
        sv.radius = (r, r)
        sv.use_root = (i == 0)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier="Skin")
    ob.select_set(False)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def skin_weights(ob, arm, J, sp, mats):
    P = np.array([v.co[:] for v in ob.data.vertices])
    names = list(J.keys())
    D = np.stack([seg_dist(P, np.array(J[n][0]), np.array(J[n][1])) for n in names], axis=1)
    W = 1.0 / (D + 0.004) ** 7
    top = np.argsort(-W, axis=1)[:, :3]
    groups = {n: ob.vertex_groups.new(name=n) for n in names}
    best = top[:, 0]
    for i in range(len(P)):
        ws = W[i, top[i]]
        ws = ws / ws.sum()
        for j, w in zip(top[i], ws):
            if w > 0.03:
                groups[names[j]].add([i], float(w), "REPLACE")
    # материалы по доминирующей кости вершины
    me = ob.data
    for m in mats["list"]:
        me.materials.append(m)
    zone = mats["zone"]
    for p in me.polygons:
        vids = list(p.vertices)
        b = names[np.bincount(best[vids]).argmax()]
        c = Vector(np.mean(P[vids], axis=0))
        p.material_index = zone(b, c)
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    sub = ob.modifiers.new("Sub", "SUBSURF")
    sub.levels, sub.render_levels = 1, 2
    ob.parent = arm


def ray_surface(bvh, origin, direction, offset):
    hit = bvh.ray_cast(origin, direction.normalized(), 10.0)
    if hit[0] is None:
        return origin + direction.normalized() * 0.1, direction.normalized()
    loc, nrm = hit[0], hit[1]
    return loc + nrm * offset, nrm


def build_head(name, sp, arm, J, colors):
    """Голова + черты лица. Возвращает словарь объектов/параметров."""
    R = sp["head_r"]
    hc = J["neck"][1] + Vector((0, 0, R * 0.62))
    skin = mat(name + "_skin", colors["skin"], rough=0.6, sss=0.0)
    head = prim("sphere", name + "_head", size=R, loc=(0, 0, 0), material=skin, segments=48, rings=32)
    me = head.data
    for v in me.vertices:
        x, y, z = v.co
        k = 1.0 + sp.get("cheek", 0.06) * max(0.0, -z / R) * (1 - abs(z / R))
        v.co = Vector((x * k * sp.get("head_sx", 1.0), y * 0.95 * k, z * sp.get("head_sz", 1.0)))
    head.location = hc
    bpy.context.view_layer.update()
    # «челюсть»: форма-ключ опускает подбородок при открытом рте
    head.shape_key_add(name="Basis")
    jaw = head.shape_key_add(name="jaw")
    for i, v in enumerate(me.vertices):
        x, y, z = v.co
        if z < -0.25 * R and y < 0:
            w = min(1.0, (-0.25 * R - z) / (0.35 * R)) * min(1.0, -y / (0.5 * R))
            jaw.data[i].co = v.co + Vector((0, -0.002 * w, -sp["jaw_drop"] * w))
    parent_to_bone(head, arm, "head")
    dg = bpy.context.evaluated_depsgraph_get()
    # BVH головы в мировых координатах (в покое)
    hm = head.matrix_world
    bvh = BVHTree.FromPolygons([hm @ v.co for v in me.vertices], [p.vertices for p in me.polygons])
    out = {"head": head, "center": hc, "R": R, "bvh": bvh}
    re = sp["eye_r"]
    white = mat("eye_white", (0.95, 0.95, 0.93), rough=0.15)
    iris_m = mat(name + "_iris", colors["iris"], rough=0.2)
    pupil_m = mat("pupil", (0.02, 0.015, 0.01), rough=0.1)
    hl_m = mat("eye_highlight", (1, 1, 1), emit=4.0)
    lash_m = mat(name + "_lash", colors.get("lash", (0.05, 0.03, 0.02)), rough=0.6)
    brow_m = mat(name + "_brow", colors["brow"], rough=0.7)
    out["eyes"] = {}
    for s, side in ((1, "L"), (-1, "R")):
        d = Vector((s * sp["eye_sep"], -1.0, sp["eye_up"])).normalized()
        ec = hc + d * R * sp["eye_depth"]
        rot = d.to_track_quat("-Y", "Z")
        ew = prim("sphere", f"{name}_eye.{side}", size=re, loc=ec, material=white, segments=32, rings=16)
        ew.rotation_mode = "QUATERNION"; ew.rotation_quaternion = rot
        ew.scale = (1, 0.92, 1)
        parent_to_bone(ew, arm, "head")
        ir = prim("sphere", f"{name}_iris.{side}", size=re * 0.62, loc=ec + d * re * 0.78, material=iris_m, segments=24, rings=12)
        ir.rotation_mode = "QUATERNION"; ir.rotation_quaternion = rot; ir.scale = (1, 0.3, 1)
        pu = prim("sphere", f"{name}_pupil.{side}", size=re * 0.33, loc=ec + d * re * 0.93, material=pupil_m, segments=20, rings=10)
        pu.rotation_mode = "QUATERNION"; pu.rotation_quaternion = rot; pu.scale = (1, 0.25, 1)
        up = Vector((0, 0, 1)); sidev = d.cross(up).normalized()
        hl = prim("sphere", f"{name}_hl.{side}", size=re * 0.13, loc=ec + (d * 0.9 + up * 0.32 - sidev * 0.22).normalized() * re * 1.0,
                  material=hl_m, segments=12, rings=6)
        for o in (ir, pu, hl):
            parent_to_bone(o, arm, f"eye.{side}")
        # верхнее веко: полусфера, поворотом вокруг поперечной оси закрывает глаз
        lid_r = re * 1.07
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=lid_r)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.02 * lid_r], context="VERTS")
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-sp.get("lid_open", 52)), 3, "X"))
        lme = bpy.data.meshes.new(f"{name}_lidup.{side}"); bm.to_mesh(lme); bm.free()
        lid = bpy.data.objects.new(lme.name, lme); link(lid); lme.materials.append(skin)
        for p in lme.polygons: p.use_smooth = True
        lid.rotation_mode = "QUATERNION"; lid.rotation_quaternion = rot; lid.location = ec
        sol = lid.modifiers.new("Sol", "SOLIDIFY"); sol.thickness = re * 0.06
        lash = torus(f"{name}_lash.{side}", lid_r * 1.01, re * 0.045, loc=ec, material=lash_m, seg=24, mseg=6, arc=math.pi)
        lash.rotation_mode = "QUATERNION"
        lash.rotation_quaternion = rot @ Quaternion((1, 0, 0), math.radians(-sp.get("lid_open", 52))) @ Quaternion((0, 0, 1), math.pi)
        parent_to_bone(lid, arm, f"lid_up.{side}"); parent_to_bone(lash, arm, f"lid_up.{side}")
        # нижнее веко: маленькая чаша снизу
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=re * 1.05)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > -0.55 * re], context="VERTS")
        lme2 = bpy.data.meshes.new(f"{name}_lidlo.{side}"); bm.to_mesh(lme2); bm.free()
        lidlo = bpy.data.objects.new(lme2.name, lme2); link(lidlo); lme2.materials.append(skin)
        for p in lme2.polygons: p.use_smooth = True
        lidlo.rotation_mode = "QUATERNION"; lidlo.rotation_quaternion = rot; lidlo.location = ec
        parent_to_bone(lidlo, arm, f"lid_lo.{side}")
        # бровь
        bd = Vector((s * sp["eye_sep"] * 0.95, -0.93, sp["eye_up"] + sp["brow_up"])).normalized()
        bp, bn = ray_surface(bvh, hc, bd, 0.004)
        brow = prim("cube", f"{name}_brow.{side}", size=1.0, loc=bp, material=brow_m, subdiv=2)
        brow.scale = (sp["brow_len"] * 2.0, 0.008, sp["brow_th"])
        brow.rotation_mode = "QUATERNION"
        brow.rotation_quaternion = bn.to_track_quat("-Y", "Z") @ Quaternion((0, 1, 0), -s * math.radians(sp.get("brow_tilt", 6)))
        parent_to_bone(brow, arm, f"brow.{side}")
        out["eyes"][side] = {"center": ec, "dir": d}
    # нос, уши, румянец
    npos, nn = ray_surface(bvh, hc, Vector((0, -1, sp["nose_up"])), -sp["nose_r"] * 0.35)
    nose = prim("sphere", name + "_nose", size=sp["nose_r"], loc=npos, material=skin, segments=20, rings=10)
    nose.scale = (1.1, 0.9, 0.85)
    parent_to_bone(nose, arm, "head")
    blush = mat(name + "_blush", colors["blush"], rough=0.6, sss=0.2)
    for s in (1, -1):
        cp, cn = ray_surface(bvh, hc, Vector((s * 0.55, -0.85, -0.22)), -0.006)
        ch = prim("sphere", f"{name}_cheek{s}", size=R * 0.16, loc=cp, material=blush, segments=16, rings=8)
        ch.rotation_mode = "QUATERNION"; ch.rotation_quaternion = cn.to_track_quat("Z", "Y"); ch.scale = (1, 0.75, 0.25)
        parent_to_bone(ch, arm, "head")
        ep = hc + Vector((s * R * sp.get("head_sx", 1.0) * 0.97, 0.02, -R * 0.08))
        ear = prim("sphere", f"{name}_ear{s}", size=R * 0.22, loc=ep, material=skin, segments=16, rings=8)
        ear.scale = (0.45, 0.75, 1.0)
        parent_to_bone(ear, arm, "head")
    out["mouth"] = build_mouth(name, sp, bvh, hc, arm, colors)
    return out


def build_mouth(name, sp, bvh, hc, arm, colors):
    """Рот: сетка на поверхности лица. Слои: губы, полость, зубы, язык. Формы-ключи для визем."""
    md = Vector((0, -1, -sp["mouth_down"])).normalized()
    ua = Vector((1, 0, 0))
    va = md.cross(ua).normalized() * -1  # вверх по лицу
    if va.z < 0:
        va = -va
    A0, B0, S0 = sp["mouth_w"], 0.0022, sp.get("mouth_smile", 0.003)
    NT, NR = 28, 4

    def shape(a, b, smile, rho_scale=1.0):
        pts = []
        for r in range(1, NR + 1):
            rho = r / NR * rho_scale
            for k in range(NT):
                th = 2 * math.pi * k / NT
                u = a * rho * math.cos(th)
                v = b * rho * math.sin(th) + smile * (u / max(a, 1e-4)) ** 2 * rho
                pts.append((u, v))
        return [(0.0, smile * 0.0)] + pts

    def faces_for(offset_idx):
        f = []
        for k in range(NT):
            f.append((offset_idx, offset_idx + 1 + k, offset_idx + 1 + (k + 1) % NT))
        for r in range(NR - 1):
            for k in range(NT):
                a0 = offset_idx + 1 + r * NT + k
                a1 = offset_idx + 1 + r * NT + (k + 1) % NT
                f.append((a0, a1, a1 + NT, a0 + NT))
        return f

    def ring_faces(offset_idx, nr):
        f = []
        for r in range(nr - 1):
            for k in range(NT):
                a0 = offset_idx + r * NT + k
                a1 = offset_idx + r * NT + (k + 1) % NT
                f.append((a0, a1, a1 + NT, a0 + NT))
        return f

    def project(uv, off):
        out = []
        for u, v in uv:
            p, n = ray_surface(bvh, hc, md * sp["head_r"] + ua * u + va * v, off)
            out.append(p)
        return out

    # параметры форм: (a, b, smile)
    params = {
        "Basis": (A0, B0, S0), "open": (A0 * 0.9, sp["mouth_open"], S0), "wide": (A0 * 1.35, B0 * 2.2, S0),
        "round": (A0 * 0.5, sp["mouth_open"] * 0.65, S0 * 0.3), "smile": (A0 * 1.15, B0, S0 + sp["mouth_w"] * 0.42),
        "frown": (A0 * 0.95, B0, S0 - sp["mouth_w"] * 0.38),
    }
    lip_m = mat(name + "_lip", colors["lip"], rough=0.45, sss=0.2)
    cav_m = mat("mouth_cavity", (0.18, 0.03, 0.04), rough=0.8)
    teeth_m = mat("teeth", (0.97, 0.96, 0.92), rough=0.3)
    tongue_m = mat("tongue", (0.85, 0.35, 0.38), rough=0.5)

    def layers(a, b, smile, teeth_on, tongue_on):
        # губы: кольцо rho 1.0..1.25 (свои вершины)
        lip_uv = []
        for rr in (1.0, 1.12, 1.25):
            for k in range(NT):
                th = 2 * math.pi * k / NT
                u = a * rr * math.cos(th)
                v = (b * rr + 0.0012 * (rr - 1) * 8) * math.sin(th) + smile * (u / max(a, 1e-4)) ** 2
                lip_uv.append((u, v))
        V = project(lip_uv, 0.0009)
        V += project(shape(a, b, smile), 0.0013)
        tt = project(shape(a * 0.92, b * 0.92, smile), 0.0019 if teeth_on else -0.006)
        tg = project(shape(a * 0.75, b * 0.8, smile * 0.8), 0.0017 if tongue_on else -0.006)
        return V, tt, tg

    nlip = 3 * NT
    ncav = 1 + NR * NT
    V, TT, TG = layers(*params["Basis"], False, False)
    teeth_faces = [f for f in faces_for(0) if all(((i - 1) % NT) < NT / 2 and i > 0 for i in f) and
                   min(((i - 1) // NT) for i in f if i > 0) >= NR - 2]
    tongue_faces = [f for f in faces_for(0) if all(i > 0 and ((i - 1) % NT) >= NT / 2 + 2 and ((i - 1) % NT) <= NT - 3 for i in f)]
    faces = ring_faces(0, 3)
    mats_idx = [0] * len(faces)
    faces += [tuple(i + nlip for i in f) for f in faces_for(0)]; mats_idx += [1] * (len(faces) - len(mats_idx))
    o_t = nlip + ncav
    faces += [tuple(i + o_t for i in f) for f in teeth_faces]; mats_idx += [2] * (len(faces) - len(mats_idx))
    o_g = o_t + ncav
    faces += [tuple(i + o_g for i in f) for f in tongue_faces]; mats_idx += [3] * (len(faces) - len(mats_idx))
    ob = new_mesh_obj(name + "_mouth", V + TT + TG, faces, mats=[lip_m, cav_m, teeth_m, tongue_m])
    for p, mi in zip(ob.data.polygons, mats_idx):
        p.material_index = mi
    ob.shape_key_add(name="Basis")
    for k, prm in params.items():
        if k == "Basis":
            continue
        sk = ob.shape_key_add(name=k)
        V2, T2, G2 = layers(*prm, False, False)
        for i, p in enumerate(V2 + T2 + G2):
            sk.data[i].co = p
    for k, (teeth_on, tongue_on) in {"teeth": (True, False), "tongue": (False, True)}.items():
        sk = ob.shape_key_add(name=k)
        V2, T2, G2 = layers(*params["Basis"], teeth_on, tongue_on)
        # зубы/язык выдвигаются ОТНОСИТЕЛЬНО базовой формы (складываются с open)
        for i, p in enumerate(V2 + T2 + G2):
            sk.data[i].co = p
    parent_to_bone(ob, arm, "head")
    return ob


def _face_frames(sp, J):
    R = sp["head_r"]
    hc = J["neck"][1] + Vector((0, 0, R * 0.62))
    fb = {}
    for s, side in ((1, "L"), (-1, "R")):
        d = Vector((s * sp["eye_sep"], -1.0, sp["eye_up"])).normalized()
        ec = hc + d * R * sp["eye_depth"]
        for b in ("eye", "lid_up", "lid_lo"):
            fb[f"{b}.{side}"] = (ec, ec + d * 0.03, "head")
        bd = Vector((s * sp["eye_sep"] * 0.95, -0.93, sp["eye_up"] + sp["brow_up"])).normalized()
        bp = hc + bd * R
        fb[f"brow.{side}"] = (bp, bp + Vector((0, -0.02, 0)), "head")
    return fb, hc


def _shell(name, R, sp, keep, material, thick):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v.co)], context="VERTS")
    for v in bm.verts:
        x, y, z = v.co
        k = 1.0 + sp.get("cheek", 0.06) * max(0.0, -z) * (1 - abs(z))
        v.co = Vector((x * k * sp.get("head_sx", 1.0), y * 0.95 * k, z * sp.get("head_sz", 1.0))) * R
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); link(ob); me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    so = ob.modifiers.new("Sol", "SOLIDIFY"); so.thickness = thick; so.offset = 1.0
    sub = ob.modifiers.new("Sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
    return ob


def create(name, sp, colors, accessories):
    J = build_skeleton(sp)
    fb, hc = _face_frames(sp, J)
    extra = {}
    if "tuft" in accessories:
        p = hc + Vector((0, 0.35, 0.9)).normalized() * sp["head_r"] * 1.02
        extra["tuft"] = (p, p + Vector((0, 0.01, 0.05)), "head")
    arm = make_armature(name, J, fb, extra)
    mats_l = [mat(name + "_" + k, c, rough=r, sss=ss) for k, c, r, ss in colors["body"]]
    body = body_mesh(name, sp, J, None)
    skin_weights(body, arm, J, sp, {"list": mats_l, "zone": colors["zone"]})
    face = build_head(name, sp, arm, J, colors)
    R = sp["head_r"]
    out = {"arm": arm, "body": body, "J": J, "face": face, "sp": sp, "name": name}
    if "hair" in accessories:
        hm = mat(name + "_hair", colors["hair"], rough=0.85)

        def keep(c):
            x, y, z = c
            if y < -0.35:
                thr = 0.40 - 0.25 * max(0.0, abs(x) - 0.3)
            elif y < 0.3:
                thr = 0.18 - 0.55 * (y + 0.35)
            else:
                thr = -0.45
            return z > thr
        hair = _shell(name + "_hair", R * 1.045, sp, keep, hm, 0.012)
        hair.location = hc
        parent_to_bone(hair, arm, "head")
        for i, (ax, az) in enumerate(((-0.35, 0.62), (-0.1, 0.70), (0.15, 0.66), (0.38, 0.58))):
            dvec = Vector((ax, -0.62, az)).normalized()
            p = hc + Vector((dvec.x * R * sp.get("head_sx", 1), dvec.y * R * 0.95, dvec.z * R)) * 1.05
            c = prim("cone", f"{name}_fringe{i}", size=R * 0.16, loc=p, material=hm, segments=12)
            c.scale = (1, 0.5, R * 0.35)
            c.rotation_mode = "QUATERNION"; c.rotation_quaternion = Vector((0.1 * ax, -0.6, -1.0)).to_track_quat("-Z", "Y")
            parent_to_bone(c, arm, "head")
    if "tuft" in accessories:
        hm = mat(name + "_hair", colors["hair"], rough=0.85)
        base = fb and extra["tuft"][0]
        for i, (tx, ty) in enumerate(((0.0, 0.0), (0.018, -0.01))):
            c = prim("cone", f"{name}_tuft{i}", size=R * 0.06, loc=base + Vector((tx, ty, 0.03)), material=hm, segments=10)
            c.scale = (1, 0.6, R * 0.32)
            c.rotation_euler = (math.radians(-25 + 30 * i), math.radians(15 - 25 * i), 0)
            parent_to_bone(c, arm, "tuft")
    if "hood" in accessories:
        hood_m = mat(name + "_hood", colors["hood"], rough=0.8, sss=0.05)
        cz = J["chest"][1].z - 0.01
        hd = torus(name + "_hood", sp["radii"]["chest"] * 0.75, 0.035, loc=(0, 0.045, cz), material=hood_m, seg=24, mseg=10,
                   arc=math.pi * 1.25, rot=(math.radians(-12), 0, math.radians(-22)))
        hd.scale = (1.0, 0.85, 1.0)
        parent_to_bone(hd, arm, "chest")
    if "watch" in accessories:
        wm = mat("watch_band", (0.08, 0.12, 0.2), rough=0.5)
        wf = mat("watch_face", (0.75, 0.9, 0.95), rough=0.2, emit=0.3)
        h, t = J["forearm.L"]
        p = h + (t - h) * 0.86
        w = torus(name + "_watch", sp["radii"]["wrist"] * 1.22, 0.007, loc=p, material=wm, seg=20, mseg=6)
        w.rotation_mode = "QUATERNION"; w.rotation_quaternion = (t - h).normalized().to_track_quat("Z", "Y")
        parent_to_bone(w, arm, "forearm.L")
        f = prim("cyl", name + "_watchface", size=0.014, loc=p + Vector((0, -sp["radii"]["wrist"] * 1.25, 0)), material=wf, segments=16)
        f.scale = (1, 1, 0.006); f.rotation_euler = (math.radians(90), 0, 0)
        parent_to_bone(f, arm, "forearm.L")
    if "scarf" in accessories:
        scm = mat(name + "_scarf", colors["scarf"], rough=0.85, sss=0.05)

        def keep(c):
            x, y, z = c
            face = y < -0.25 and (x / 0.70) ** 2 + ((z + 0.08) / 0.64) ** 2 < 1.0
            return not face
        sc = _shell(name + "_scarf", R * 1.07, sp, keep, scm, 0.014)
        for v in sc.data.vertices:
            zu = v.co.z / R
            if zu < -0.45:
                k = (-0.45 - zu)
                v.co.z -= k * 0.9 * R
                v.co.x *= 1 + k * 1.6; v.co.y *= 1 + k * 1.3
        sc.location = hc + Vector((0, 0.008, 0.01))
        parent_to_bone(sc, arm, "head")
        kn = prim("sphere", name + "_knot", size=R * 0.16, loc=hc + Vector((0.02, -R * 0.78, -R * 1.02)), material=scm, segments=16, rings=8)
        kn.scale = (1.2, 0.8, 0.9)
        parent_to_bone(kn, arm, "head")
    if "glasses" in accessories:
        gm = mat("glasses", (0.35, 0.22, 0.12), rough=0.3, metal=0.3)
        for side in "LR":
            e = face["eyes"][side]
            g = torus(f"{name}_glass.{side}", sp["eye_r"] * 1.35, 0.0028, loc=e["center"] + e["dir"] * sp["eye_r"] * 1.55, material=gm, seg=28, mseg=6)
            g.rotation_mode = "QUATERNION"; g.rotation_quaternion = e["dir"].to_track_quat("Z", "Y")
            parent_to_bone(g, arm, "head")
        pl, pr = [face["eyes"][s]["center"] + face["eyes"][s]["dir"] * sp["eye_r"] * 1.55 for s in "LR"]
        br = prim("cyl", name + "_bridge", size=0.003, loc=(pl + pr) / 2 + Vector((0, -0.004, 0.006)), material=gm, segments=8)
        br.scale = (1, 1, (pl - pr).length - sp["eye_r"] * 2.6); br.rotation_euler = (0, math.radians(90), 0)
        parent_to_bone(br, arm, "head")
    shoe_m = mat(name + "_shoe", colors["shoe"], rough=0.45)
    sole_m = mat(name + "_sole", colors.get("sole", (0.9, 0.9, 0.88)), rough=0.6)
    for side in "LR":
        a0, a1 = J["foot." + side][0], J["toe." + side][1]
        c = Vector(((a0.x + a1.x) / 2, (a0.y + a1.y) / 2 - 0.01, sp["shoe_h"] * 0.55))
        L = (a1 - a0).length + 0.04
        sh = prim("sphere", f"{name}_shoe.{side}", size=1.0, loc=c, material=shoe_m, segments=24, rings=12)
        sh.scale = (sp["shoe_w"], L * 0.55, sp["shoe_h"] * 0.6)
        so = prim("sphere", f"{name}_sole.{side}", size=1.0, loc=c + Vector((0, 0, -sp["shoe_h"] * 0.22)), material=sole_m, segments=24, rings=8)
        so.scale = (sp["shoe_w"] * 1.04, L * 0.56, sp["shoe_h"] * 0.22)
        parent_to_bone(sh, arm, "foot." + side); parent_to_bone(so, arm, "foot." + side)
    if "skirt" in accessories:
        skm = mat(name + "_skirt", colors["skirt"], rough=0.85, sss=0.05)
        ztop, zbot = sp["leg"] + 0.13, sp["skirt_hem"]
        rings, seg = 8, 40
        verts, faces = [], []
        for r in range(rings + 1):
            h = r / rings
            z = ztop + (zbot - ztop) * h
            rad = sp["radii"]["pelvis"] * 0.80 + (sp["skirt_r"] - sp["radii"]["pelvis"] * 0.80) * (h ** 0.6)
            for k in range(seg):
                a = 2 * math.pi * k / seg
                verts.append((rad * math.cos(a), rad * math.sin(a) * 0.85, z))
        for r in range(rings):
            for k in range(seg):
                a0, a1 = r * seg + k, r * seg + (k + 1) % seg
                faces.append((a0, a1, a1 + seg, a0 + seg))
        sk = new_mesh_obj(name + "_skirtmesh", verts, faces, mats=[skm])
        gp, gl, gr = (sk.vertex_groups.new(name=n) for n in ("pelvis", "thigh.L", "thigh.R"))
        for i, (x, y, z) in enumerate(verts):
            h = (ztop - z) / (ztop - zbot)
            wl = 0.6 * h * min(1, max(0, 0.5 + x / 0.3))
            wr = 0.6 * h - wl
            gp.add([i], 1 - 0.6 * h, "REPLACE"); gl.add([i], wl, "REPLACE"); gr.add([i], wr, "REPLACE")
        so = sk.modifiers.new("Sol", "SOLIDIFY"); so.thickness = 0.008
        m = sk.modifiers.new("Armature", "ARMATURE"); m.object = arm
        sub = sk.modifiers.new("Sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
        sk.parent = arm
    setup_ik(out)
    return out


def setup_ik(ch):
    arm, J, sp, name = ch["arm"], ch["J"], ch["sp"], ch["name"]
    E = {}

    def empty(n, loc, parent=None, size=0.05):
        e = bpy.data.objects.new(f"{name}_{n}", None)
        e.empty_display_size = size
        link(e)
        e.location = loc
        if parent:
            e.parent = parent
        e.rotation_mode = "XYZ"
        E[n] = e
        return e

    for s in "LR":
        rest_foot = arm.data.bones["foot." + s].matrix_local
        ef = empty("ik_foot." + s, J["foot." + s][0])
        ef.matrix_world = Matrix.Translation(J["foot." + s][0]) @ rest_foot.to_3x3().to_4x4()
        empty("pole_knee." + s, J["shin." + s][0] + Vector((0, -0.6, 0)), parent=arm)
        c = arm.pose.bones["shin." + s].constraints.new("IK")
        c.target = ef; c.pole_target = E["pole_knee." + s]; c.chain_count = 2; c.pole_angle = math.radians(sp.get("pole_angle", -90))
        cr = arm.pose.bones["foot." + s].constraints.new("COPY_ROTATION")
        cr.target = ef
        rest_hand = arm.data.bones["hand." + s].matrix_local
        eh = empty("ik_hand." + s, J["hand." + s][0])
        eh.matrix_world = Matrix.Translation(J["hand." + s][0]) @ rest_hand.to_3x3().to_4x4()
        sgn = 1 if s == "L" else -1
        empty("pole_elbow." + s, J["forearm." + s][0] + Vector((sgn * 0.25, 0.5, -0.1)), parent=arm)
        c = arm.pose.bones["forearm." + s].constraints.new("IK")
        c.target = eh; c.pole_target = E["pole_elbow." + s]; c.chain_count = 2
        c.pole_angle = math.radians(sp.get("arm_pole_angle", -90)); c.influence = 0.0
        cr = arm.pose.bones["hand." + s].constraints.new("COPY_ROTATION")
        cr.target = eh; cr.influence = 0.0
    g = empty("gaze", ch["face"]["center"] + Vector((0, -2.0, 0)), size=0.1)
    for s in "LR":
        c = arm.pose.bones["eye." + s].constraints.new("DAMPED_TRACK")
        c.target = g; c.track_axis = "TRACK_Y"
    ch["E"] = E
