"""Общие функции для сборки сцены в Blender (bpy 5.2)."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler

MATS = {}


def mat(name, color, rough=0.6, sss=0.0, metal=0.0, emit=0.0, spec=0.3):
    """Материал для обоих стилей: узлы Principled (EEVEE) + diffuse_color (Workbench/2D)."""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.roughness = rough
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = spec
    if sss > 0:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = (0.9, 0.45, 0.3)
        p.inputs["Subsurface Scale"].default_value = 0.02
    if emit > 0:
        p.inputs["Emission Color"].default_value = (*color, 1.0)
        p.inputs["Emission Strength"].default_value = emit
    MATS[name] = m
    return m


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def new_mesh_obj(name, verts, faces, edges=(), mats=(), smooth=True, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], list(edges), [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    for m in mats:
        me.materials.append(m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


def prim(kind, name, size=1.0, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), material=None,
         segments=32, rings=16, subdiv=0, smooth=True, coll=None):
    """Примитив через bmesh (без bpy.ops) — быстро и без зависимости от контекста."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if kind == "sphere":
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=size)
    elif kind == "ico":
        bmesh.ops.create_icosphere(bm, subdivisions=max(1, subdiv), radius=size)
    elif kind == "cube":
        bmesh.ops.create_cube(bm, size=size)
    elif kind == "cyl":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=size, radius2=size, depth=1.0)
    elif kind == "cone":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=size, radius2=size * 0.5, depth=1.0)
    elif kind == "torus":
        pass
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    ob.location = loc
    ob.scale = scale
    ob.rotation_euler = rot
    if material:
        me.materials.append(material)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if subdiv and kind != "ico":
        m = ob.modifiers.new("Sub", "SUBSURF")
        m.levels = subdiv
        m.render_levels = subdiv
    return ob


def torus(name, R, r, loc=(0, 0, 0), rot=(0, 0, 0), material=None, seg=32, mseg=10, arc=2 * math.pi, coll=None):
    verts, faces = [], []
    n = seg + (0 if arc >= 2 * math.pi - 1e-6 else 1)
    for i in range(n):
        a = arc * i / seg
        for j in range(mseg):
            b = 2 * math.pi * j / mseg
            verts.append(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    closed = arc >= 2 * math.pi - 1e-6
    for i in range(seg if closed else seg):
        i2 = (i + 1) % n if closed else i + 1
        if not closed and i2 >= n:
            break
        for j in range(mseg):
            j2 = (j + 1) % mseg
            faces.append((i * mseg + j, i2 * mseg + j, i2 * mseg + j2, i * mseg + j2))
    ob = new_mesh_obj(name, verts, faces, mats=[material] if material else [], coll=coll)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def parent_to_bone(obj, arm, bone_name):
    """Привязать объект к кости, сохранив его текущее положение в мире (в позе покоя)."""
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone_name]
    M = arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.length, 0))
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_parent_inverse = M.inverted()
    obj.matrix_basis = world


def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


class Ch:
    """Анимационный канал: ключи (t, value), плавная интерполяция (smootherstep) между ключами."""

    def __init__(self, keys=None, default=0.0):
        self.keys = sorted(keys or [], key=lambda k: k[0])
        self.default = default

    def add(self, t, v):
        self.keys.append((t, v))
        self.keys.sort(key=lambda k: k[0])
        return self

    def __call__(self, t):
        k = self.keys
        if not k:
            return self.default
        if t <= k[0][0]:
            return k[0][1]
        if t >= k[-1][0]:
            return k[-1][1]
        for (t0, v0), (t1, v1) in zip(k, k[1:]):
            if t0 <= t <= t1:
                if t1 == t0:
                    return v1
                s = smoothstep((t - t0) / (t1 - t0))
                return v0 + (v1 - v0) * s
        return k[-1][1]


def noise1(t, seed=0.0, freq=0.5):
    """Гладкий псевдошум (сумма синусов) для микродвижений."""
    return (math.sin(t * freq * 6.283 + seed * 1.7) * 0.5 + math.sin(t * freq * 2.71 * 6.283 + seed * 3.1) * 0.3
            + math.sin(t * freq * 5.13 * 6.283 + seed * 5.3) * 0.2)
