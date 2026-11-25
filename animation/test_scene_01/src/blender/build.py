"""Сборка тестовой сцены «Лифт не работает» (15–20 с) и рендер в двух стилях.

Запуск (Blender как модуль Python, bpy 5.2):
  python build.py --audio BUILD/audio --out BUILD --style 3d|2d [--render] [--res 1920 1080]
                  [--frames 1 579] [--step 1] [--save-blend]
"""
import sys, os, json, math, argparse, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Euler
import numpy as np
import common
from common import Ch, smoothstep, mat
import character, specs, environment, animation as an

FPS = 30
DUR = 19.3
N = int(round(DUR * FPS))  # 579 кадров
T = lambda f: f / FPS
F = lambda t: int(round(t * FPS))


class Channels(dict):
    DEF = {"breath_rate": 0.28, "breath_amp": 0.35, "curl": 0.3, "teeth_smile": 1.0, "ua_z": -0.30, "fa_x": 0.22}

    def __missing__(self, k):
        base = k.rsplit("_", 1)[0] if k.endswith(("_L", "_R")) else k
        d = 1.0 if base in ("swing", "ikrot") else self.DEF.get(base, 0.0)
        self[k] = Ch([], default=d)
        return self[k]

    def keys_(self, name, *pairs):
        self[name] = Ch(list(pairs))
        return self[name]


def wrap_gaze(schedule, n, seed):
    """schedule: [(t, target)], target: Vector или callable(f)->Vector. Саккады 3 кадра + микросаккады."""
    rnd = random.Random(seed)
    micro = {}
    tt = 0.3
    while tt < DUR:
        micro[F(tt)] = Vector((rnd.uniform(-1, 1), 0, rnd.uniform(-1, 1))) * 0.012
        tt += rnd.uniform(0.5, 1.1)
    def tgt(spec, f):
        return spec(f) if callable(spec) else spec
    def g(f):
        t = T(f)
        cur = schedule[0]
        prev = None
        for s in schedule:
            if s[0] <= t:
                prev, cur = cur, s
        p = tgt(cur[1], f)
        if prev is not None and t - cur[0] < 0.1:
            q = tgt(prev[1], f)
            p = q.lerp(p, smoothstep((t - cur[0]) / 0.1))
        mk = max([k for k in micro if k <= f], default=None)
        return p + (micro[mk] if mk is not None else Vector())
    return g


def make_root(keys_xy, keys_yaw, vel_profile=None):
    cx, cy = Ch([(t, p[0]) for t, p in keys_xy]), Ch([(t, p[1]) for t, p in keys_xy])
    cyaw = Ch(keys_yaw)
    pos = [Vector((cx(T(f)), cy(T(f)), 0)) for f in range(N)]
    yaw = [cyaw(T(f)) for f in range(N)]
    return pos, yaw


def run_root(start, stop, t_run_end, t_stop, v0):
    """Бег с постоянной скоростью, затем плавное торможение до точки stop."""
    u = (stop - start).normalized()
    dist = (stop - start).length
    # v(t)=v0 до t_run_end, затем v0*(1-smoothstep) до t_stop; интеграл подогнан масштабом
    ts = np.arange(N) / FPS
    v = np.where(ts < t_run_end, v0, v0 * (1 - np.array([smoothstep((x - t_run_end) / (t_stop - t_run_end)) for x in ts])))
    d = np.concatenate([[0], np.cumsum(v[1:] / FPS)])
    d *= dist / d[min(N - 1, F(t_stop) + 2)]
    d = np.minimum(d, dist)
    return [start + u * float(x) for x in d], u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default="3d", choices=["3d", "2d"])
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--res", nargs=2, type=int, default=[1920, 1080])
    ap.add_argument("--frames", nargs=2, type=int, default=[1, N])
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--save-blend", action="store_true")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    os.makedirs(a.out, exist_ok=True)
    lines = json.load(open(os.path.join(a.audio, "phonemes.json")))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, N
    environment.build_environment()
    P = environment.build_props()
    amir = character.create("amir", specs.AMIR, dict(specs.AMIR_COLORS, zone=specs.amir_zone(specs.AMIR)), ["hair", "tuft", "hood", "watch"])
    baba = character.create("babushka", specs.BABUSHKA, dict(specs.BABUSHKA_COLORS, zone=specs.babushka_zone(specs.BABUSHKA)), ["scarf", "glasses", "skirt"])

    # ------------------------------------------------------------ расстановка
    BAG_A = Vector((-0.04, -0.10, 0.0))
    BAG_B = Vector((0.98, 0.05, 0.0))
    P["bag_a"].location = BAG_A + Vector((0, 0, 0.34)); P["bag_a"].rotation_euler = (0, 0, math.radians(20))
    P["bag_b"].location = BAG_B + Vector((0, 0, 0.46)); P["bag_b"].rotation_euler = (0, 0, math.radians(-15))
    A_STOP = Vector((-0.32, 0.18, 0))
    A_START = Vector((-4.2, -0.10, 0))
    G_POS = Vector((0.62, 0.20, 0))
    YAW_A = math.radians(40)
    YAW_G = math.radians(-44)

    # ------------------------------------------------------------ АМИР: корень
    run_pos, u = run_root(A_START, A_STOP, 0.75, 2.75, 2.6)
    run_yaw = math.atan2(u.x, -u.y)
    yawA = Ch([(0, run_yaw), (2.45, run_yaw), (3.05, YAW_A), (18.30, YAW_A), (18.85, math.radians(-95))])
    walk_end = Ch([(18.65, 0.0), (19.3, 0.62)])
    posA, yawAl = [], []
    for f in range(N):
        t = T(f)
        p = run_pos[f].copy()
        if t > 18.65:
            p = A_STOP + Vector((-(t - 18.65) * 0.95, 0, 0))
        posA.append(p); yawAl.append(yawA(t))

    # ------------------------------------------------------------ БАБУШКА: корень
    yawG = Ch([(0, math.radians(140)), (1.75, math.radians(140)), (2.55, math.radians(316)), (18.5, math.radians(316)), (19.2, math.radians(290))])
    gstep = Ch([(16.15, 0.0), (16.45, 1.0)])
    posG = [G_POS + Vector((-0.10, -0.035, 0)) * gstep(T(f)) for f in range(N)]
    yawGl = [yawG(T(f)) for f in range(N)]

    def head_world(ch, pos, yaw, f, crouch=0.0):
        return pos[f] + Vector((0, 0, ch["face"]["center"].z - crouch))

    # ------------------------------------------------------------ каналы АМИРА
    CA = Channels()
    CA.keys_("crouch", (0, 0), (2.55, 0), (2.85, 0.045), (3.3, 0.005), (12.0, 0.0), (12.35, 0.17), (12.72, 0.18), (13.05, 0.02), (13.35, 0.04),
             (16.6, 0.04), (17.0, 0.02), (18.3, 0.04))
    CA.keys_("lean", (0, 0), (2.55, 0), (2.9, 0.16), (3.6, 0.03), (6.6, 0.03), (6.9, 0.08), (7.3, 0.06), (7.55, -0.07), (7.95, 0.02),
             (9.75, 0.02), (9.95, 0.07), (10.35, 0.0), (12.0, 0.0), (12.35, 0.62), (12.72, 0.62), (13.05, 0.08), (13.4, 0.03))
    CA.keys_("side", (12.9, 0), (13.15, -0.16), (13.5, -0.10), (19.3, -0.10))
    CA.keys_("twist", (12.0, 0), (12.3, -0.22), (12.8, -0.12), (13.2, 0.0))
    CA.keys_("shrug", (7.35, 0), (7.55, 0.6), (7.9, 0), (13.0, 0), (13.1, 0.5), (13.35, -0.2), (13.6, 0))
    CA.keys_("breath_amp", (0, 0.35), (2.7, 1.0), (4.5, 0.6), (6.5, 0.3))
    CA.keys_("breath_rate", (0, 0.3), (2.7, 0.75), (5.5, 0.35))
    CA.keys_("head_pitch", (7.35, 0), (7.55, -0.22), (7.95, 0), (12.9, 0), (13.05, -0.12), (13.4, 0.0))
    CA.keys_("head_roll", (2.9, 0), (3.2, 0.06), (3.6, 0), (8.0, 0), (8.3, 0.14), (9.6, 0.10), (9.9, 0), (13.5, 0), (13.8, -0.13), (15.0, 0),
             (16.7, 0), (17.0, 0.08), (17.8, 0))
    # правая рука держит мяч до 10.9, затем отпускает; хват сумки — IK
    CA.keys_("ua_x_R", (0, 0.10), (10.85, 0.10), (11.05, 0.45), (11.35, 0.05))
    CA.keys_("ua_z_R", (0, 0.32), (10.85, 0.32), (11.2, -0.25))
    CA.keys_("ua_y_R", (0, -0.4), (10.85, -0.4), (11.2, 0.0))
    CA.keys_("fa_x_R", (0, 1.45), (10.85, 1.45), (11.05, 0.55), (11.35, 0.25))
    CA.keys_("swing_R", (0, 0.0), (11.0, 0.0), (11.3, 1.0))
    CA.keys_("curl_R", (0, 0.55), (10.85, 0.55), (10.95, 0.08), (12.3, 0.1), (12.48, 0.15), (12.58, 0.95), (19.3, 0.95))
    CA.keys_("ik_R", (12.05, 0.0), (12.4, 1.0), (19.3, 1.0))
    CA.keys_("ikrot_R", (0, 0.7))
    # левая рука: бег — мах; часы (IK); жест «у меня матч»
    CA.keys_("ik_L", (6.55, 0.0), (6.85, 1.0), (7.2, 1.0), (7.45, 0.0))
    CA.keys_("ikrot_L", (0, 1.0))
    CA.keys_("ua_x_L", (8.45, 0.0), (8.75, 0.55), (9.5, 0.5), (9.8, 0.0))
    CA.keys_("ua_z_L", (0, -0.3), (8.45, -0.3), (8.75, 0.25), (9.5, 0.2), (9.8, -0.3))
    CA.keys_("fa_x_L", (0, 0.2), (8.45, 0.2), (8.75, 1.25), (9.5, 1.2), (9.8, 0.25))
    CA.keys_("fa_y_L", (8.45, 0.0), (8.75, 1.3), (9.5, 1.3), (9.8, 0.0))
    CA.keys_("curl_L", (0, 0.35), (8.5, 0.35), (8.75, 0.05), (9.5, 0.08), (9.8, 0.35))
    # лицо Амира
    CA.keys_("brow_up", (0, 0.1), (2.55, 0.1), (2.85, 0.9), (3.6, 0.3), (6.5, 0.25), (6.8, 0.0), (8.0, 0.3), (9.7, 0.4), (10.3, 0.0),
             (12.9, 0.0), (13.0, 1.0), (13.5, 0.6), (13.7, 0.2), (16.5, 0.3), (17.0, 0.5), (18.0, 0.2))
    CA.keys_("brow_inner", (0, 0.0), (7.3, 0.0), (7.6, 0.6), (8.0, 0.75), (9.7, 0.7), (10.2, 0.1), (10.45, -0.35), (11.6, -0.2), (12.4, -0.3),
             (12.9, 0.0), (13.6, 0.0), (16.5, 0.0), (17.0, 0.2), (18.0, 0.0))
    CA.keys_("brow_asym", (13.55, 0), (13.8, 0.8), (14.8, 0.6), (15.1, 0))
    CA.keys_("smile", (0, 0.15), (2.6, 0.1), (3.0, 0.35), (3.6, 0.25), (6.6, 0.1), (7.4, 0.0), (9.8, 0.0), (10.5, 0.5), (11.6, 0.6),
             (12.4, 0.2), (12.95, 0.0), (13.6, 0.0), (13.8, 0.75), (15.0, 0.6), (16.6, 0.7), (16.9, 1.0), (18.2, 0.8))
    CA.keys_("frown", (7.3, 0), (7.6, 0.5), (8.0, 0.35), (9.7, 0.3), (10.2, 0.0), (12.3, 0.0), (12.6, 0.5), (12.9, 0.0))
    CA.keys_("lid", (0, 0.0), (2.6, 0.0), (2.85, 0.35), (3.5, 0.0), (7.3, 0.0), (7.5, -0.5), (7.9, -0.15), (9.7, -0.15), (10.3, 0.05),
             (12.95, 0.0), (13.05, 0.45), (13.5, 0.1), (13.8, -0.1), (15.0, 0.0))
    CA.keys_("lid_lo", (13.7, 0), (13.9, 0.45), (15.0, 0.2), (16.7, 0.2), (17.0, 0.8), (18.0, 0.4))
    CA.keys_("open_add", (2.6, 0.0), (2.75, 0.25), (3.4, 0.08), (5.5, 0.0), (7.45, 0.0), (7.6, 0.3), (7.9, 0.0), (12.9, 0.0), (13.0, 0.25), (13.2, 0.0))

    def gb_head(f):
        return head_world(baba, posG, yawGl, f) + Vector((0, 0, 0.0))

    def amir_head(f):
        return head_world(amir, posA, yawAl, f, CA["crouch"](T(f)))

    def ahead(f):
        return posA[f] + an.yaw_vec(yawAl[f]) * 3 + Vector((0, 0, 0.9))

    def watch_pt(f):
        return posA[f] + an.yaw_vec(yawAl[f]) * 0.20 + Vector((0, 0, 0.70))

    gazeA = wrap_gaze([(0, ahead), (2.35, gb_head), (5.15, BAG_A + Vector((0, 0, 0.2))), (5.55, gb_head), (6.65, watch_pt),
                       (7.4, lambda f: amir_head(f) + Vector((0.3, 0.4, 1.5))), (7.9, gb_head), (9.8, BAG_A + Vector((0, 0, 0.25))),
                       (10.15, BAG_B + Vector((0, 0, 0.3))), (10.35, gb_head), (11.0, lambda f: ball_pos_hint(f)), (11.6, gb_head),
                       (12.0, BAG_A + Vector((0, 0, 0.3))), (13.0, gb_head), (14.4, lambda f: posA[f] + an.side_vec(yawAl[f]) * -0.3 + Vector((0, 0, 0.3))),
                       (14.75, gb_head), (18.25, lambda f: posA[f] + Vector((-3, 0, 0.8)))], N, 11)

    def ball_pos_hint(f):
        return posA[f] + an.yaw_vec(yawAl[f]) * 0.6 + Vector((0, -0.3, 0.1))

    def ik_watch(f):
        yaw = yawAl[f]
        p = posA[f] + an.yaw_vec(yaw) * 0.19 + an.side_vec(yaw) * 0.02 + Vector((0, 0, 0.66 - CA["crouch"](T(f))))
        Y = (-an.side_vec(yaw)).normalized()
        Z = (Vector((0, 0, 1)) - an.yaw_vec(yaw) * 0.45).normalized()
        X = Y.cross(Z).normalized(); Z = X.cross(Y)
        R = Matrix((X, Y, Z)).transposed()
        return p, R

    def ik_bag(f):
        t = T(f)
        yaw = yawAl[f]
        handle = BAG_A + Vector((0, 0, 0.36))
        side = posA[f] - an.side_vec(yaw) * 0.205 + an.yaw_vec(yaw) * 0.03 + Vector((0, 0, 0.45 - CA["crouch"](t) * 0.9))
        if t < 12.72:
            p = handle
        else:
            k = smoothstep((t - 12.72) / 0.4)
            p = handle.lerp(side, k)
        Y = Vector((0, 0, -1)); Z = an.yaw_vec(yaw)
        X = Y.cross(Z).normalized(); Z = X.cross(Y)
        return p, Matrix((X, Y, Z)).transposed()

    A = {"ch": amir, "C": CA, "pos": posA, "yaw": yawAl, "gaze": gazeA, "seed": 1.0,
         "ik_targets": {"L": ik_watch, "R": ik_bag}}
    visA, mbpA, stressA, talkA = an.viseme_track(lines, "amir", N)
    A["vis"], A["stress"] = visA, stressA
    turnsA = [2.35, 6.65, 9.8, 13.0, 18.25]
    A["blink"], A["blink_times"] = an.blink_track(N, 3, forced=turnsA)

    # ------------------------------------------------------------ каналы БАБУШКИ
    CG = Channels()
    CG.keys_("crouch", (0, 0.035), (2.6, 0.0))
    CG.keys_("lean", (0, 0.22), (1.8, 0.22), (2.6, 0.08), (9.8, 0.08), (10.0, 0.18), (10.5, 0.08), (16.2, 0.08), (16.6, 0.16), (17.5, 0.16), (17.9, 0.08))
    CG.keys_("breath_amp", (0, 1.0), (3.0, 0.6), (6.0, 0.3))
    CG.keys_("breath_rate", (0, 0.6), (3.0, 0.4), (6.0, 0.25))
    CG.keys_("head_yaw", (9.0, 0), (9.12, 0.12), (9.28, -0.12), (9.44, 0.1), (9.6, 0))
    CG.keys_("head_pitch", (14.3, 0), (14.45, 0.08), (14.6, -0.02), (14.75, 0.08), (14.9, 0))
    CG.keys_("head_roll", (3.6, 0), (4.0, -0.08), (6.5, -0.05), (8.9, -0.05), (9.2, 0.1), (10.0, 0.0), (15.4, 0), (15.8, -0.1), (18.4, 0))
    CG.keys_("shrug", (14.3, 0), (14.42, 0.35), (14.55, 0), (14.68, 0.35), (14.82, 0))
    # левая рука на пояснице (IK), правая — указывает на сумки, потом жест, потом похлопать по плечу (IK)
    CG.keys_("ik_L", (0, 1.0), (2.1, 1.0), (2.55, 0.0), (9.8, 0.0), (10.0, 1.0), (10.6, 1.0), (10.95, 0.0))
    CG.keys_("ikrot_L", (0, 0.3))
    CG.keys_("ua_x_R", (4.55, 0.0), (4.9, 0.5), (5.5, 0.45), (5.85, 0.0), (15.6, 0), (15.95, 0.35), (16.3, 0.2))
    CG.keys_("ua_z_R", (0, -0.4), (4.55, -0.4), (4.9, 0.1), (5.5, 0.1), (5.85, -0.4))
    CG.keys_("fa_x_R", (0, 0.15), (4.55, 0.15), (4.9, 0.35), (5.5, 0.35), (5.85, 0.15), (15.6, 0.15), (15.95, 1.0), (16.3, 0.4))
    CG.keys_("fa_y_R", (15.6, 0), (15.95, 1.1), (16.3, 0.4))
    CG.keys_("point_R", (4.6, 0), (4.85, 1.0), (5.5, 1.0), (5.8, 0.0))
    CG.keys_("curl_R", (0, 0.35), (4.6, 0.35), (4.85, 0.85), (5.5, 0.85), (5.8, 0.35), (15.6, 0.35), (15.95, 0.05), (16.4, 0.15), (17.5, 0.15), (17.9, 0.35))
    CG.keys_("ua_z_L", (0, -0.4))
    CG.keys_("ik_R", (16.45, 0.0), (16.75, 1.0), (17.45, 1.0), (17.8, 0.0))
    CG.keys_("ikrot_R", (0, 0.4))
    CG.keys_("brow_up", (0, 0.0), (1.8, 0.0), (2.2, 0.6), (2.8, 0.3), (3.6, 0.35), (6.5, 0.2), (8.9, 0.4), (9.6, 0.2), (13.0, 0.3), (13.2, 0.7), (14.0, 0.3))
    CG.keys_("brow_inner", (0, 0.6), (1.8, 0.6), (2.4, 0.2), (3.6, 0.45), (6.5, 0.3), (9.8, 0.2), (10.0, 0.8), (10.5, 0.3), (11.0, 0.0))
    CG.keys_("smile", (0, 0.0), (1.9, 0.0), (2.4, 0.45), (3.6, 0.35), (5.6, 0.55), (6.5, 0.4), (8.9, 0.45), (9.3, 0.75), (9.8, 0.3), (10.0, 0.0),
             (10.6, 0.3), (11.0, 0.8), (12.9, 0.6), (13.3, 1.0), (15.2, 0.8), (17.0, 1.0), (19.3, 0.8))
    CG.keys_("frown", (9.85, 0), (10.0, 0.5), (10.5, 0.2), (10.8, 0))
    CG.keys_("lid", (0, -0.35), (1.8, -0.35), (2.3, 0.1), (3.0, 0.0), (9.9, 0.0), (10.05, -0.45), (10.5, -0.1), (11.0, 0.0))
    CG.keys_("lid_lo", (0, 0.0), (11.0, 0.3), (13.2, 0.4), (13.5, 0.8), (15.2, 0.4), (16.8, 0.8), (18.5, 0.5))
    CG.keys_("teeth_smile", (0, 0.6))

    def amir_shoulder_L(f):
        return amir_shoulders[f] if amir_shoulders else posA[f] + Vector((0, 0, 0.75))

    def g_ik_back(f):
        yaw = yawGl[f]
        p = posG[f] - an.yaw_vec(yaw) * 0.17 + an.side_vec(yaw) * 0.10 + Vector((0, 0, specs.BABUSHKA["leg"] + 0.08))
        return p, None

    def g_ik_pat(f):
        t = T(f)
        pats = sum(0.035 * math.exp(-((t - pt) / 0.06) ** 2) for pt in (16.85, 17.2))
        return amir_shoulder_L(f) + Vector((0, 0, 0.045 + pats)), None

    gazeG = wrap_gaze([(0, Vector((1.55, 2.0, 1.5))), (1.65, lambda f: posA[f] + Vector((0, 0, 0.8))), (2.45, amir_head),
                       (4.7, BAG_A + Vector((0, 0, 0.2))), (5.1, amir_head), (9.85, lambda f: posG[f] + an.yaw_vec(yawGl[f]) * 0.8),
                       (10.4, amir_head), (12.2, BAG_A + Vector((0, 0, 0.3))), (13.0, amir_head),
                       (16.45, lambda f: amir_shoulder_L(f)), (17.45, amir_head), (18.55, lambda f: posA[f] + Vector((-1.5, 0, 0.6)))], N, 22)
    B = {"ch": baba, "C": CG, "pos": posG, "yaw": yawGl, "gaze": gazeG, "seed": 4.0,
         "ik_targets": {"L": g_ik_back, "R": g_ik_pat}}
    visG, mbpG, stressG, talkG = an.viseme_track(lines, "babushka", N)
    B["vis"], B["stress"] = visG, stressG
    B["blink"], B["blink_times"] = an.blink_track(N, 9, forced=[1.7, 2.45, 10.4, 16.45])

    # ------------------------------------------------------------ запекание: Амир -> оценка плеча -> бабушка
    rec = an.Rec(N)
    qa = an.bake_actor(A, rec, N)
    rec.write()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in meshes:
        o.hide_viewport = True
    amir_shoulders = []
    ball_track, bag_track = [], []
    arm = amir["arm"]
    for f in range(N):
        sc.frame_set(f + 1)
        pbm = arm.pose.bones["clav.L"]
        amir_shoulders.append(arm.matrix_world @ pbm.tail)
        fr = arm.matrix_world @ arm.pose.bones["forearm.R"].matrix
        hd = arm.matrix_world @ arm.pose.bones["hand.R"].matrix
        ball_track.append(fr.copy()); bag_track.append(hd.copy())
    qg = an.bake_actor(B, rec, N)
    rec.write()

    # ------------------------------------------------------------ мяч: несёт под рукой -> бросает -> отскоки
    REL = F(10.9)
    ref = F(4.0)
    hip_side = posA[ref] - an.side_vec(yawAl[ref]) * 0.16 + an.yaw_vec(yawAl[ref]) * 0.06 + Vector((0, 0, 0.53))
    off = ball_track[ref].inverted() @ hip_side
    ball = P["ball"]
    r = 0.105
    bounces = []
    bp = [None] * N
    for f in range(REL + 1):
        bp[f] = ball_track[f] @ off
    v = (bp[REL] - bp[REL - 2]) * (FPS / 2) + an.yaw_vec(yawAl[REL]) * 0.9 + Vector((0, 0, -0.6)) - an.side_vec(yawAl[REL]) * 0.3
    p = bp[REL].copy()
    spin = Vector((0, 0, 0)); rot = Matrix.Identity(3); rots = [Matrix.Identity(3)] * N
    for f in range(REL + 1, N):
        dt = 1 / FPS
        sub = 4
        for _ in range(sub):
            h = dt / sub
            v.z -= 9.81 * h
            p += v * h
            if p.z < r:
                p.z = r
                if v.z < -0.25:
                    bounces.append((T(f), float(-v.z)))
                v.z = -v.z * 0.6 if v.z < -0.25 else 0.0
                v.x *= 0.985; v.y *= 0.985
            if p.z <= r + 1e-4:
                hv = Vector((v.x, v.y, 0))
                if hv.length > 0:
                    hv = hv * max(0.0, 1 - 0.5 * h / max(hv.length, 1e-3))
                    v.x, v.y = hv.x, hv.y
            if p.y > environment.WALL_Y - 0.14 - r:
                p.y = environment.WALL_Y - 0.14 - r; v.y = -abs(v.y) * 0.5; bounces.append((T(f), abs(v.y)))
        bp[f] = p.copy()
        hv = Vector((v.x, v.y, 0))
        if hv.length > 1e-4:
            axis = Vector((0, 0, 1)).cross(hv).normalized()
            rot = Matrix.Rotation(hv.length / FPS / r, 3, axis) @ rot
        rots[f] = rot.copy()
    for f in range(N):
        if f <= REL:
            M = ball_track[f] @ Matrix.Translation(off)
            rec.vec(ball, "location", f, M.translation)
            eu = M.to_euler("XYZ", rec_prev(ball))
        else:
            rec.vec(ball, "location", f, bp[f])
            eu = (rots[f] @ ball_track[REL].to_3x3()).to_euler("XYZ", rec_prev(ball))
        set_prev(ball, eu)
        rec.vec(ball, "rotation_euler", f, eu)

    # ------------------------------------------------------------ сумка: хват в 12.56 c, затем висит на руке с маятником
    GRAB = F(12.56)
    bag = P["bag_a"]
    rest = bag.matrix_world.copy()
    grip_local = None
    ang, angv = 0.0, 0.0
    prev = None
    bag_pts = []
    for f in range(N):
        if f < GRAB:
            rec.vec(bag, "location", f, rest.translation)
            rec.vec(bag, "rotation_euler", f, rest.to_euler())
            bag_pts.append(rest.translation.copy())
            continue
        hd = bag_track[f]
        grip = hd @ Vector((0, arm.pose.bones["hand.R"].length * 0.95, 0.0))
        k = smoothstep((f - GRAB) / 8)
        base = rest.translation
        pos = base.lerp(grip, k) if f < GRAB + 8 else grip
        acc = Vector((0, 0, 0))
        if prev is not None and len(bag_pts) >= 2:
            acc = (pos - 2 * bag_pts[-1] + bag_pts[-2]) * FPS * FPS
        fwd = an.yaw_vec(yawAl[f])
        angv += (-(acc.dot(fwd)) * 0.012 - 30 * math.sin(ang) - 2.5 * angv) / FPS
        ang += angv / FPS
        prev = pos
        bag_pts.append(pos.copy())
        yaw = yawAl[f] + math.pi / 2
        R = Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(-ang * k, 3, "Y")
        rec.vec(bag, "location", f, pos)
        eu = R.to_euler("XYZ", rec_prev(bag)); set_prev(bag, eu)
        rec.vec(bag, "rotation_euler", f, eu)
    rec.write()
    for o in meshes:
        o.hide_viewport = False

    # ------------------------------------------------------------ камеры (монтаж)
    AH = Vector((A_STOP.x, A_STOP.y, 0.92)); GH = Vector((G_POS.x - 0.08, G_POS.y - 0.03, 1.20))
    u = (GH - AH); u.z = 0; u.normalize()
    lat = Vector((0, -1, 0))
    cam_g = AH - u * 0.55 + lat * 0.42 + Vector((0, 0, 0.10))   # через плечо Амира на бабушку
    cam_a = GH + u * 0.45 + lat * 0.45 + Vector((0, 0, -0.22))  # через плечо бабушки на Амира
    shots = [
        ("C1_wide", 0.0, (-0.35, -3.55, 1.12), lambda t: Vector((-2.0 + 1.85 * smoothstep((t - 0.3) / 2.7), 0.3, 0.70)), 28),
        ("C2_baba", 3.3, tuple(cam_g), lambda t: GH + Vector((0, 0, -0.04)), 34),
        ("C3_amir", 6.55, tuple(cam_a), lambda t: AH + Vector((0, 0, -0.06)), 34),
        ("C4_side", 10.4, (-0.55, -2.2, 0.9), lambda t: Vector((0.12, 0.0, 0.50 + 0.06 * smoothstep((t - 12.5) / 1.0))), 30),
        ("C3b_amir", 12.95, tuple(cam_a + Vector((0.05, -0.15, -0.05))), lambda t: AH + Vector((0, 0, -0.12)), 30),
        ("C2b_baba", 15.2, tuple(cam_g + Vector((-0.05, -0.12, -0.02))), lambda t: (GH + AH) / 2 + Vector((0.12, 0, 0.02)), 30),
        ("C6_exit", 17.75, (-0.55, -2.7, 1.05), lambda t: Vector((-0.45 - 0.3 * smoothstep((t - 18.3) / 1.0), 0.1, 0.62)), 30),
    ]
    for i, (nm, t0, loc, tgt, lens) in enumerate(shots):
        cam = bpy.data.objects.new(nm, bpy.data.cameras.new(nm)); sc.collection.objects.link(cam)
        cam.data.lens = lens
        cam.data.dof.use_dof = False
        cam.data.dof.aperture_fstop = 2.8
        t1 = shots[i + 1][1] if i + 1 < len(shots) else DUR
        for f in range(F(t0), min(N, F(t1) + 1)):
            t = T(f)
            drift = Vector((0.03 * math.sin(t * 0.4 + i), 0.0, 0.01 * math.sin(t * 0.3 + i)))
            L = Vector(loc) + drift
            look = tgt(t)
            q = (look - L).to_track_quat("-Z", "Y")
            rec.vec(cam, "location", f, L)
            rec.vec(cam, "rotation_euler", f, q.to_euler())
            # фокус на говорящем/главном
            rec.set(cam.data, "dof.focus_distance", 0, f, (look - L).length)
        m = sc.timeline_markers.new(nm, frame=F(t0) + 1)
        m.camera = cam
        if i == 0:
            sc.camera = cam
    rec.write()

    blob_shadows(a.style, sc, rec, [amir["arm"], baba["arm"]], ball, bp, bag, bag_pts, P["bag_b"])
    rec.write()
    setup_style(a.style, sc)
    events = {"amir_steps": [(T(e[0]), e[2]) for e in A["gait_events"]], "baba_steps": [(T(e[0]), e[2]) for e in B["gait_events"]],
              "ball_bounces": bounces, "ball_release": T(REL), "bag_grab": T(GRAB),
              "pats": [16.85, 17.2], "watch_beep": 7.0, "sigh": [7.35, 7.95]}
    json.dump(events, open(os.path.join(a.out, "events.json"), "w"), indent=1)
    qc = {"fps": FPS, "frames": N,
          "amir": {"mbp_frames": mbpA, "mouth_closed_frames": qa["mouth_closed_frames"], "blinks_s": qa["blinks"]},
          "babushka": {"mbp_frames": mbpG, "mouth_closed_frames": qg["mouth_closed_frames"], "blinks_s": qg["blinks"]},
          "feet_amir": foot_report(A, N), "feet_babushka": foot_report(B, N)}
    json.dump(qc, open(os.path.join(a.out, "anim_qc.json"), "w"), indent=1)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(a.out, f"scene_{a.style}.blend"), compress=True)
    if a.render:
        sc.render.resolution_x, sc.render.resolution_y = a.res
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        frames_dir = os.path.join(a.out, f"frames_{a.style}")
        os.makedirs(frames_dir, exist_ok=True)
        import time
        t0 = time.time()
        for fr in range(a.frames[0], a.frames[1] + 1, a.step):
            out = os.path.join(frames_dir, f"{fr:04d}.png")
            if os.path.exists(out):
                continue
            sc.frame_set(fr)
            sc.render.filepath = out
            bpy.ops.render.render(write_still=True)
            print(f"frame {fr} {time.time() - t0:.0f}s", flush=True)


_PREV = {}


def blob_shadows(style, sc, rec, rigs, ball, ball_pts, bag, bag_pts, bag_b):
    """2D: мягкие контактные тени-пятна на полу (как в рисованной анимации). В 3D скрыты — там реальные тени."""
    m = mat("blob_shadow", (0.30, 0.21, 0.16), rough=1.0)
    def disc(name, rx, ry):
        o = common.prim("sphere", name, size=1.0, material=m, segments=24, rings=6)
        o.scale = (rx, ry, 0.002)
        o.hide_render = style != "2d"
        return o
    for r in rigs:
        d = disc(r.name + "_blob", 0.24 if "babushka" in r.name else 0.18, 0.17 if "babushka" in r.name else 0.13)
        d.parent = r; d.location = (0, 0, 0.003)
    db = disc("ball_blob", 0.1, 0.1)
    for f, p in enumerate(ball_pts):
        if p is None:
            p = ball.matrix_world.translation
        h = max(0.0, p.z - 0.105)
        rec.vec(db, "location", f, (p.x, p.y, 0.003))
        k = 1.0 / (1 + 2.5 * h)
        rec.vec(db, "scale", f, (0.11 * k, 0.11 * k, 0.002))
    dg = disc("bag_a_blob", 0.17, 0.09)
    for f, p in enumerate(bag_pts):
        h = max(0.0, p.z - 0.34)
        k = 1.0 / (1 + 3 * h)
        rec.vec(dg, "location", f, (p.x, p.y, 0.003))
        rec.vec(dg, "scale", f, (0.17 * k, 0.09 * k, 0.002))
    d2 = disc("bag_b_blob", 0.2, 0.11)
    d2.location = (bag_b.location.x, bag_b.location.y, 0.003)


def rec_prev(o):
    return _PREV.get(o.name, Euler((0, 0, 0)))


def set_prev(o, e):
    _PREV[o.name] = e


def foot_report(A, n):
    """Скольжение стоп: смещение стопы, пока она стоит на полу (по данным походки)."""
    worst = 0.0
    for s in "LR":
        G = A["feet"][s]
        for f in range(1, n):
            p0, _, _, sw0 = G[f - 1]
            p1, _, _, sw1 = G[f]
            if not sw0 and not sw1:
                worst = max(worst, (p1 - p0).length)
    return {"max_planted_slide_m": round(worst, 5), "steps": len(A["gait_events"])}


def setup_style(style, sc):
    world = bpy.data.worlds.new("world"); sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.42, 0.45, 0.50, 1); bg.inputs[1].default_value = 0.55
    if style == "3d":
        sc.render.engine = "BLENDER_EEVEE"
        e = sc.eevee
        e.taa_render_samples = 6
        e.use_raytracing = False
        e.shadow_ray_count = 1
        e.shadow_step_count = 4
        sc.render.use_motion_blur = False
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
        lights = [
            ("key", "AREA", (-1.6, -2.2, 2.6), (1.0, 0.93, 0.82), 260, 1.6),
            ("fill", "AREA", (2.4, -2.6, 1.6), (0.75, 0.85, 1.0), 110, 2.0),
            ("ceiling", "POINT", (0.3, 0.2, 2.75), (1.0, 0.85, 0.65), 70, 0.3),
            ("window", "AREA", (-0.1, 2.15, 1.7), (0.75, 0.88, 1.0), 140, 0.9),
        ]
        for nm, kind, loc, col, energy, size in lights:
            L = bpy.data.lights.new(nm, kind); L.color = col; L.energy = energy
            if kind == "AREA":
                L.size = size
            else:
                L.shadow_soft_size = size
            o = bpy.data.objects.new(nm, L); sc.collection.objects.link(o); o.location = loc
            o.rotation_euler = (Vector((0.1, 0.2, 0.7)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 2.2; sun.color = (1.0, 0.92, 0.8); sun.angle = math.radians(4)
        so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
        so.rotation_euler = (math.radians(55), 0, math.radians(165))
    else:
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_shadows = False  # тени Workbench дают артефакты; в 2D — контактные тени-пятна (см. blob_shadows)
        sh.show_object_outline = True
        sh.object_outline_color = (0.08, 0.05, 0.05)
        sh.show_cavity = True
        sh.cavity_type = "BOTH"
        sh.cavity_ridge_factor = 0.4; sh.cavity_valley_factor = 1.0
        sh.show_specular_highlight = False
        sc.display.light_direction = (-0.45, -0.55, 0.70)
        sc.display.shadow_shift = 0.15
        sc.display.shadow_focus = 0.9
        sc.display.render_aa = "16"
        sc.view_settings.view_transform = "Standard"
        load_toon_light(sh)
        # незамкнутые/мелкие меши дают «лучи» в теневых объёмах Workbench — не отбрасывают тень
        for o in bpy.data.objects:
            if o.type in ("MESH", "FONT") and any(k in o.name for k in ("mouth", "lash", "iris", "pupil", "_hl.", "brow", "cheek",
                                                                         "glass", "bridge", "handle", "sign", "door_num", "lid", "eye", "fringe",
                                                                         "tuft", "watch", "sky", "lamp", "stud", "knob", "leaf", "flower", "floor", "hood", "ceiling")):
                o.display.show_shadows = False


def load_toon_light(sh):
    """2D-стиль: «плоский» студийный свет из двух тонов (cel-shading)."""
    prefs = bpy.context.preferences
    try:
        sl = prefs.studio_lights
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toon_matcap.png")
        if not os.path.exists(path):
            make_toon_matcap(path)
        m = sl.load(path, "MATCAP")
        sh.light = "MATCAP"
        sh.studio_light = m.name
    except Exception as ex:
        print("matcap fallback:", ex)
        sh.light = "FLAT"


def make_toon_matcap(path, size=256):
    yy, xx = np.mgrid[0:size, 0:size]
    nx = (xx - size / 2) / (size / 2); ny = (size / 2 - yy) / (size / 2)
    r2 = nx ** 2 + ny ** 2
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    L = np.array([-0.45, 0.55, 0.70]); L = L / np.linalg.norm(L)
    d = nx * L[0] + ny * L[1] + nz * L[2]
    tone = np.where(d > 0.05, 1.0, 0.84)
    tone = np.where(d > 0.85, 1.06, tone)
    tone[r2 > 1] = 0.84
    img = bpy.data.images.new("toon", size, size)
    px = np.ones((size, size, 4), dtype=np.float32)
    for c in range(3):
        px[..., c] = np.clip(tone, 0, 1)
    img.pixels.foreach_set(px[::-1].ravel())
    img.filepath_raw = path; img.file_format = "PNG"; img.save()


if __name__ == "__main__":
    main()
