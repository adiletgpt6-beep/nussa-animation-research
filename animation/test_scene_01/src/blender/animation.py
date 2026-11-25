"""Анимационная система: каналы-ключи + процедурные слои, запись F-кривых массивом.

Слои: корень и походка (постановка стоп без скольжения), таз, позвоночник, голова (автоповорот за
взглядом с опережением глаз), руки FK/IK, пальцы, глаза (саккады, моргания), веки, брови, рот (lip sync
по фонемам Piper + эмоции), вторичное движение (хохолок).
"""
import bpy, math, random
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
from common import Ch, noise1, smoothstep

FPS = 30


def lerp(a, b, t):
    return a + (b - a) * t


class Rec:
    """Собирает значения каналов по кадрам и пишет F-кривые разом (foreach_set)."""

    def __init__(self, nframes):
        self.n = nframes
        self.data = {}  # (id_block, path, index) -> np.array

    def set(self, obj, path, idx, f, v):
        if isinstance(obj, bpy.types.ID):
            idb = obj
        else:  # PoseBone, Constraint, ShapeKey, CameraDOF ... -> владелец + полный путь
            idb, path = obj.id_data, obj.path_from_id(path)
        k = (idb, path, idx)
        a = self.data.get(k)
        if a is None:
            a = self.data[k] = np.full(self.n, np.nan)
        a[f] = v

    def vec(self, idb, path, f, vals):
        for i, v in enumerate(vals):
            self.set(idb, path, i, f, v)

    def write(self):
        lin = bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value
        for (idb, path, idx), arr in self.data.items():
            if idb.animation_data is None:
                idb.animation_data_create()
            if idb.animation_data.action is None:
                idb.animation_data.action = bpy.data.actions.new(idb.name + "_act")
            act = idb.animation_data.action
            fc = act.fcurve_ensure_for_datablock(idb, path, index=idx)
            fr = np.where(~np.isnan(arr))[0]
            if len(fr) == 0:
                continue
            fc.keyframe_points.clear()
            fc.keyframe_points.add(len(fr))
            co = np.empty(2 * len(fr)); co[0::2] = fr + 1; co[1::2] = arr[fr]
            fc.keyframe_points.foreach_set("co", co)
            fc.keyframe_points.foreach_set("interpolation", [lin] * len(fr))
            fc.update()
        self.data = {}


# ---------------------------------------------------------------- походка

def yaw_vec(yaw):
    return Vector((math.sin(yaw), -math.cos(yaw), 0))


def side_vec(yaw):  # «влево» персонажа (+X локально)
    return Vector((math.cos(yaw), math.sin(yaw), 0))


def gait(root_pos, root_yaw, sp, n, run_thr=1.5):
    """Постановка стоп. root_pos[f]: Vector(x,y,0), root_yaw[f]. Возвращает по кадрам:
    стопы (pos, yaw, pitch), фаза, скорость, режим, события касаний."""
    dt = 1.0 / FPS
    vel = [Vector((0, 0, 0))] + [(root_pos[i] - root_pos[i - 1]) / dt for i in range(1, n)]
    spd = [v.length for v in vel]
    sm = spd[:]
    for i in range(n):  # сглаживание скорости
        a, b = max(0, i - 3), min(n, i + 4)
        sm[i] = sum(spd[a:b]) / (b - a)
    hw = sp["leg_w"]
    feet = {"L": None, "R": None}
    out = {"L": [None] * n, "R": [None] * n}
    phase = [0.0] * n
    events = []  # (frame, side, kind)
    # 1) фазовый проход для движения
    ph = 0.0
    swings = []  # (side, f0, f1, from, to, yaw_to, lift)
    last_td = {"L": -100, "R": -100}
    plant = {s: (root_pos[0] + side_vec(root_yaw[0]) * (hw if s == "L" else -hw), root_yaw[0]) for s in "LR"}
    pending = {}
    for f in range(n):
        v = sm[f]
        if v > 0.2:
            step = 0.22 + 0.17 * v
            prev = ph
            ph += v * dt / (2 * step)
            for s, off in (("L", 0.0), ("R", 0.5)):
                if math.floor(prev - off) != math.floor(ph - off):
                    # касание стопы s в кадре f
                    runb = smoothstep((v - 1.1) / 0.8)
                    cyc = 2 * step / max(v, 0.3)
                    swing_frac = lerp(0.42, 0.64, runb)
                    sw = max(5, int(round(swing_frac * cyc * FPS)))
                    lead = step * lerp(0.28, 0.18, runb)
                    yw = root_yaw[f]
                    to = root_pos[f] + yaw_vec(yw) * lead + side_vec(yw) * (hw if s == "L" else -hw)
                    swings.append([s, f - sw, f, None, to, yw, lerp(0.07, 0.15, runb), runb])
        phase[f] = ph
    # 2) шаги-«досадки» на месте: если стопа далеко от идеальной стойки
    swings.sort(key=lambda x: x[2])
    busy_until = {"L": -1, "R": -1}
    for sw in swings:
        busy_until[sw[0]] = max(busy_until[sw[0]], sw[2])
    cur = {s: plant[s] for s in "LR"}
    timeline = {s: [] for s in "LR"}
    for sw in swings:
        timeline[sw[0]].append(sw)
    last_any = -100
    for f in range(n):
        if sm[f] > 0.2:
            continue
        for s in "LR":
            if f <= busy_until[s] or f <= busy_until["L" if s == "R" else "R"] or f - last_any < 6:
                continue
            yw = root_yaw[f]
            ideal = root_pos[f] + side_vec(yw) * (hw * 1.15 if s == "L" else -hw * 1.15)
            # текущая позиция стопы = цель последнего шага
            last = [w for w in timeline[s] if w[2] <= f]
            lw = max(last, key=lambda w: w[2]) if last else None
            pos = lw[4] if lw else plant[s][0]
            pyaw = lw[5] if lw else plant[s][1]
            dyaw = abs((yw - pyaw + math.pi) % (2 * math.pi) - math.pi)
            if (pos - ideal).length > 0.06 or dyaw > math.radians(25):
                sw = [s, f, f + 9, None, ideal, yw, 0.05, 0.0]
                timeline[s].append(sw)
                busy_until[s] = f + 9
                last_any = f
    # 3) по кадрам: позиция стопы
    for s in "LR":
        tl = sorted(timeline[s], key=lambda x: x[2])
        prev_pos, prev_yaw = plant[s]
        k = 0
        for f in range(n):
            while k < len(tl) and tl[k][2] < f:
                prev_pos, prev_yaw = tl[k][4], tl[k][5]
                k += 1
            if k < len(tl) and tl[k][1] <= f <= tl[k][2]:
                sw = tl[k]
                u = (f - sw[1]) / max(1, sw[2] - sw[1])
                us = smoothstep(u) if sw[7] < 0.5 else u
                p = prev_pos.lerp(sw[4], us)
                z = math.sin(math.pi * u) ** 0.8 * sw[6]
                yw = prev_yaw + ((sw[5] - prev_yaw + math.pi) % (2 * math.pi) - math.pi) * us
                pitch = math.radians(-35 * math.sin(math.pi * min(1, u * 1.6)) * (1 - u) + 18 * smoothstep((u - 0.6) / 0.4) * (1 - smoothstep((u - 0.92) / 0.08)))
                out[s][f] = (Vector((p.x, p.y, z)), yw, pitch * (0.4 + 0.6 * sw[7]), True)
                if f == sw[2]:
                    events.append((f, s, "run" if sw[7] > 0.5 else ("walk" if sw[6] > 0.055 else "shuffle")))
            else:
                out[s][f] = (Vector((prev_pos.x, prev_pos.y, 0)), prev_yaw, 0.0, False)
    return out, phase, sm, sorted(events)


# ---------------------------------------------------------------- лицо

VIS = {  # open, wide, round, teeth, tongue, jaw
    "A": (0.85, 0.15, 0.0, 0.55, 0.35, 0.9), "O": (0.6, 0.0, 0.75, 0.3, 0.0, 0.6), "U": (0.25, 0.0, 1.0, 0.1, 0.0, 0.3),
    "I": (0.25, 0.8, 0.0, 0.8, 0.0, 0.25), "E": (0.45, 0.55, 0.0, 0.7, 0.3, 0.45), "Y": (0.3, 0.5, 0.0, 0.6, 0.0, 0.3),
    "MBP": (0.0, 0.05, 0.0, 0.0, 0.0, 0.0), "FV": (0.1, 0.35, 0.0, 1.0, 0.0, 0.1), "S": (0.12, 0.6, 0.0, 1.0, 0.0, 0.1),
    "SH": (0.25, 0.0, 0.6, 0.8, 0.0, 0.2), "T": (0.3, 0.3, 0.0, 0.5, 0.8, 0.3), "K": (0.4, 0.2, 0.0, 0.4, 0.0, 0.4),
    "R": (0.3, 0.2, 0.0, 0.5, 0.6, 0.3), "J": (0.15, 0.6, 0.0, 0.6, 0.0, 0.15), "X": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
}
IPA = {}
for c in "aɑʌəɐ": IPA[c] = "A"
for c in "oɔ": IPA[c] = "O"
for c in "uʊ": IPA[c] = "U"
for c in "iɪ": IPA[c] = "I"
for c in "eɛ": IPA[c] = "E"
for c in "ɨy": IPA[c] = "Y"
for c in "mbp": IPA[c] = "MBP"
for c in "fv": IPA[c] = "FV"
for c in "szʦ": IPA[c] = "S"
for c in "ʃʒɕʂʐ": IPA[c] = "SH"
for c in "tdnlɫɭ": IPA[c] = "T"
IPA["r"] = "R"; IPA["ɾ"] = "R"
for c in "kgɡx": IPA[c] = "K"
IPA["j"] = "J"


def viseme_track(lines, who, n, lead_frames=1.0):
    """Кадровые веса визем по фонемам Piper. Возвращает массив (n, 6) и список кадров «м/б/п»."""
    W = np.zeros((n, 6))
    talking = np.zeros(n)
    mbp_frames = []
    stress = []
    for ln in lines:
        if ln["who"] != who:
            continue
        ph = ln["phonemes"]
        # слить ʲ и ударения с соседями
        seg = []
        pend_stress = False
        stress_start = None
        for p in ph:
            c = p["ph"]
            if c in ("ˈ", "ˌ"):
                # длительность знака ударения относится к следующей (ударной) гласной
                pend_stress = True
                stress_start = p["s"] if stress_start is None else stress_start
                continue
            if c == "ʲ" and seg:
                seg[-1][2] = p["e"]; continue
            vis = IPA.get(c, "X")
            if c in (",", ".", "!", "?", " ", "^", "$", "…", "-"):
                vis = "X"
            start = p["s"]
            if stress_start is not None:
                if vis in "AOUIEY":
                    start = stress_start; stress_start = None
                elif seg:
                    pass
            seg.append([vis, start, p["e"], pend_stress and vis in "AOUIEY"])
            if vis in "AOUIEY":
                pend_stress = False
        for vis, s, e, st in seg:
            if vis == "X" and e - s < 0.08:
                continue
            f0 = (s * FPS) - lead_frames
            f1 = (e * FPS) - lead_frames
            amp = 1.0 if vis != "A" else 1.0
            for f in range(max(0, int(math.floor(f0))), min(n, int(math.ceil(f1)) + 1)):
                ov = min(f + 0.5, f1) - max(f - 0.5, f0)
                if ov <= 0:
                    continue
                W[f] += np.array(VIS[vis]) * ov * amp
                if vis != "X":
                    talking[f] = 1
            if vis == "MBP":
                fc = int(round((s + e) / 2 * FPS - lead_frames))
                mbp_frames.append(fc)
            if st:
                stress.append(s)
    # нормировка по перекрытию + сглаживание (коартикуляция)
    W = np.clip(W, 0, 1.2)
    K = np.array([0.2, 0.6, 0.2])
    Ws = np.stack([np.convolve(W[:, i], K, mode="same") for i in range(6)], axis=1)
    for fc in mbp_frames:  # губы обязательно смыкаются
        if 0 <= fc < n:
            Ws[fc, :] = 0
            for d in (-1, 1):
                if 0 <= fc + d < n:
                    Ws[fc + d, :] *= 0.7
    return Ws, mbp_frames, stress, talking


def blink_track(n, seed, forced=()):
    """Моргания: случайные 2–5 с + принудительные (на поворотах головы). 0=открыто, 1=закрыто."""
    rnd = random.Random(seed)
    B = np.zeros(n)
    times = []
    t = rnd.uniform(0.8, 2.0)
    while t < n / FPS:
        times.append(t)
        t += rnd.uniform(2.0, 4.8)
    for ft in forced:
        if all(abs(ft - x) > 0.6 for x in times):
            times.append(ft)
    times.sort()
    shape = [0.45, 1.0, 1.0, 0.7, 0.35, 0.12]  # 2 кадра закрытия, 2 закрыто, 3 открытия
    for tt in times:
        f0 = int(tt * FPS)
        for i, v in enumerate(shape):
            if 0 <= f0 + i < n:
                B[f0 + i] = max(B[f0 + i], v)
    return B, times


# ---------------------------------------------------------------- запекание персонажа

def look_angles(head_pos, yaw, target):
    d = target - head_pos
    c, s_ = math.cos(-yaw), math.sin(-yaw)
    lx, ly = d.x * c - d.y * s_, d.x * s_ + d.y * c
    hyaw = math.atan2(lx, -ly)
    hp = math.atan2(-d.z, math.hypot(lx, ly))
    return hyaw, hp


def bake_actor(A, rec, n):
    """A: dict с ch (персонаж), pos/yaw (по кадрам), C (каналы Ch), gaze (функция f->Vector),
    vis (визем-трек), blink, ik_targets {side: f->(Vector, Matrix3|None)}, seed."""
    ch, C = A["ch"], A["C"]
    arm, sp, E = ch["arm"], ch["sp"], ch["E"]
    pb = arm.pose.bones
    G, phase, speed, events = gait(A["pos"], A["yaw"], sp, n)
    A["gait_events"] = events
    A["feet"] = G
    rest_foot = {s: arm.data.bones["foot." + s].matrix_local.to_3x3() for s in "LR"}
    rest_hand = {s: arm.data.bones["hand." + s].matrix_local.to_3x3() for s in "LR"}
    head_z = ch["face"]["center"].z
    sm_yaw = sm_pitch = 0.0
    tuft_a = tuft_v = 0.0
    prev_root = A["pos"][0].copy()
    prev_vel = Vector((0, 0, 0))
    vis = A["vis"]
    mouth = ch["face"]["mouth"].data.shape_keys
    headkey = ch["face"]["head"].data.shape_keys
    ank = {s: ch["J"]["foot." + s][0].z for s in "LR"}
    stress = A.get("stress", [])
    out = {"mouth_closed_frames": [], "blinks": A["blink_times"], "lid": []}
    for f in range(n):
        t = f / FPS
        pos, yaw = A["pos"][f], A["yaw"][f]
        rec.vec(arm, "location", f, (pos.x, pos.y, 0.0))
        rec.vec(arm, "rotation_euler", f, (0.0, 0.0, yaw))
        v = speed[f]
        runb = smoothstep((v - 1.1) / 0.8)
        walkb = smoothstep(v / 0.6) * (1 - runb)
        ph = phase[f] * 2 * math.pi
        # стопы
        for s in "LR":
            fp, fy, pitch, _ = G[s][f]
            M = Matrix.Translation((fp.x, fp.y, ank[s] + fp.z)) @ (Matrix.Rotation(fy, 3, "Z") @ Matrix.Rotation(pitch, 3, "X") @ rest_foot[s]).to_4x4()
            e = E["ik_foot." + s]
            rec.vec(e, "location", f, M.translation)
            prev = A.setdefault("_fe" + s, Euler((0, 0, 0)))
            eu = M.to_euler("XYZ", prev); A["_fe" + s] = eu
            rec.vec(e, "rotation_euler", f, eu)
        # таз: покачивание, вертикаль, присед
        breath_rate = C["breath_rate"](t)
        A["_br"] = A.get("_br", 0.0) + breath_rate / FPS
        br = math.sin(2 * math.pi * A["_br"]) * C["breath_amp"](t)
        bob = runb * (0.035 * math.cos(2 * ph) - 0.012) + walkb * (0.010 * math.cos(2 * ph + math.pi))
        sway = walkb * 0.012 * math.sin(ph) + 0.004 * noise1(t, A["seed"], 0.25)
        crouch = C["crouch"](t)
        rec.vec(pb["pelvis"], "location", f, (sway, bob - crouch - 0.01 * runb, 0.0))
        twist = 0.10 * (runb + 0.6 * walkb) * math.sin(ph)
        rec.vec(pb["pelvis"], "rotation_euler", f, (0.04 * runb, twist + C["hip_twist"](t), 0.0))
        lean = 0.20 * runb + 0.05 * walkb + C["lean"](t)
        rec.vec(pb["spine"], "rotation_euler", f, (lean * 0.5 + br * 0.01, -twist * 0.6 + C["twist"](t) * 0.5, C["side"](t) * 0.5))
        rec.vec(pb["chest"], "rotation_euler", f, (lean * 0.5 - br * 0.035, -twist * 0.9 + C["twist"](t) * 0.5, C["side"](t) * 0.5))
        for s, sg in (("L", 1), ("R", -1)):
            rec.vec(pb["clav." + s], "rotation_euler", f, (0.0, 0.0, sg * (br * 0.03 + C["shrug"](t) * 0.25)))
        # голова: автоповорот за взглядом (с запаздыванием) + ручные смещения + кивки на ударениях
        g = A["gaze"](f)
        hp = pos + Vector((0, 0, head_z - C["crouch"](t)))
        ay, apch = look_angles(hp, yaw, g)
        ay = max(-1.2, min(1.2, ay)); apch = max(-0.6, min(0.7, apch))
        k = 0.22
        sm_yaw += (ay - sm_yaw) * k
        sm_pitch += (apch - sm_pitch) * k
        nod = sum(0.06 * math.exp(-((t - st - 0.08) / 0.09) ** 2) for st in stress)
        hn = noise1(t, A["seed"] + 2, 0.35)
        hyaw = 0.62 * sm_yaw + C["head_yaw"](t) + 0.02 * hn
        hpit = 0.55 * sm_pitch + C["head_pitch"](t) + nod + 0.012 * noise1(t, A["seed"] + 5, 0.4) - lean * 0.6
        hroll = C["head_roll"](t) + 0.015 * noise1(t, A["seed"] + 7, 0.3)
        rec.vec(pb["neck"], "rotation_euler", f, (hpit * 0.35, hyaw * 0.35, hroll * 0.4))
        rec.vec(pb["head"], "rotation_euler", f, (hpit * 0.65, hyaw * 0.65, hroll * 0.6))
        # руки FK + IK
        for s, sg in (("L", 1), ("R", -1)):
            swing = (0.55 * runb + 0.28 * walkb) * math.sin(ph + (0 if s == "L" else math.pi)) * C["swing_" + s](t)
            ua = (C["ua_x_" + s](t) + swing, C["ua_y_" + s](t), sg * (C["ua_z_" + s](t) + 0.08 * runb))
            fa = (C["fa_x_" + s](t) + 0.9 * runb * C["swing_" + s](t) + 0.25 * walkb + max(0, swing) * 0.6, C["fa_y_" + s](t), 0.0)
            rec.vec(pb["upperarm." + s], "rotation_euler", f, ua)
            rec.vec(pb["forearm." + s], "rotation_euler", f, fa)
            rec.vec(pb["hand." + s], "rotation_euler", f, (C["hand_x_" + s](t), 0.0, sg * C["hand_z_" + s](t)))
            ik = C["ik_" + s](t)
            rec.set(pb["forearm." + s].constraints[0], "influence", 0, f, ik)
            rec.set(pb["hand." + s].constraints[0], "influence", 0, f, ik * C["ikrot_" + s](t))
            tgt = A["ik_targets"].get(s)
            if tgt is not None:
                tp, tr = tgt(f)
                eh = E["ik_hand." + s]
                rec.vec(eh, "location", f, tp)
                R3 = tr if tr is not None else Matrix.Rotation(yaw, 3, "Z") @ rest_hand[s]
                prev = A.setdefault("_he" + s, Euler((0, 0, 0)))
                eu = R3.to_euler("XYZ", prev); A["_he" + s] = eu
                rec.vec(eh, "rotation_euler", f, eu)
            curl = C["curl_" + s](t) + 0.25 * runb
            idx = curl * (1 - C["point_" + s](t))
            cs = -sg * A.get("curl_sign", 1)
            for fn in ("index", "middle", "ring"):
                c = idx if fn == "index" else curl
                rec.vec(pb[f"{fn}1.{s}"], "rotation_euler", f, (0.0, 0.0, cs * c * 1.25))
                rec.vec(pb[f"{fn}2.{s}"], "rotation_euler", f, (0.0, 0.0, cs * c * 1.35))
            rec.vec(pb[f"thumb1.{s}"], "rotation_euler", f, (0.0, 0.0, cs * curl * 0.6))
            rec.vec(pb[f"thumb2.{s}"], "rotation_euler", f, (0.0, 0.0, cs * curl * 0.7))
        # глаза
        rec.vec(E["gaze"], "location", f, g)
        blink = A["blink"][f]
        eye_pitch = apch - (0.55 * sm_pitch + C["head_pitch"](t))
        lid_base = C["lid"](t) * math.radians(25)
        up_angle = lid_base - blink * math.radians(sp.get("lid_open", 50) + 48) - 0.45 * eye_pitch - C["lid_lo"](t) * 0.1
        lo_angle = C["lid_lo"](t) * math.radians(28) + blink * math.radians(6)
        for s in "LR":
            rec.vec(pb["lid_up." + s], "rotation_euler", f, (up_angle, 0.0, 0.0))
            rec.vec(pb["lid_lo." + s], "rotation_euler", f, (lo_angle, 0.0, 0.0))
        out["lid"].append(blink)
        # брови
        stress_b = sum(0.5 * math.exp(-((t - st) / 0.12) ** 2) for st in stress)
        bu = C["brow_up"](t) + stress_b
        bi = C["brow_inner"](t)
        asym = C["brow_asym"](t)
        for s, sg in (("L", 1), ("R", -1)):
            up = (bu + (asym if s == "L" else -asym * 0.3)) * 0.0065
            rec.vec(pb["brow." + s], "location", f, (0.0, 0.0, up - max(0, -bi) * 0.002))
            rec.vec(pb["brow." + s], "rotation_euler", f, (0.0, -sg * bi * 0.35, 0.0))
        # рот: виземы + эмоции
        o, w, r, te, tg, jw = vis[f]
        oa = C["open_add"](t)
        sm = C["smile"](t) * (1 - 0.7 * r) * (1 - 0.3 * o)
        kb = mouth.key_blocks
        rec.set(kb["open"], "value", 0, f, min(1.0, o + oa))
        rec.set(kb["wide"], "value", 0, f, min(1.0, w))
        rec.set(kb["round"], "value", 0, f, min(1.0, r + oa * 0.6))
        rec.set(kb["smile"], "value", 0, f, sm)
        rec.set(kb["frown"], "value", 0, f, C["frown"](t) * (1 - o))
        gate = min(1.0, (o + oa) * 3.0 + w * 1.5 + sm * 0.6)
        rec.set(kb["teeth"], "value", 0, f, min(1.0, te + 0.5 * C["smile"](t) * C["teeth_smile"](t)) * gate)
        rec.set(kb["tongue"], "value", 0, f, min(1.0, tg) * min(1.0, (o + oa) * 3.0))
        rec.set(headkey.key_blocks["jaw"], "value", 0, f, min(1.0, jw + oa))
        if o + oa + w + r < 0.02:
            out["mouth_closed_frames"].append(f)
        # вторичное: хохолок
        vel = (pos - prev_root) * FPS
        acc = (vel - prev_vel) * FPS
        prev_root, prev_vel = pos.copy(), vel
        if "tuft" in pb:
            force = -acc.length * 0.004 * (1 if acc.dot(yaw_vec(yaw)) > 0 else -1) - (bob - A.get("_pbob", bob)) * FPS * 0.3
            A["_pbob"] = bob
            tuft_v += (force - 40 * tuft_a - 5 * tuft_v) / FPS
            tuft_a += tuft_v / FPS
            rec.vec(pb["tuft"], "rotation_euler", f, (max(-0.6, min(0.6, tuft_a)), 0.0, 0.0))
    return out
