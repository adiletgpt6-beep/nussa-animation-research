"""Актёр: персонаж + дорожки ключей + автоматические слои (дыхание, моргание, походка, lip sync,
кивки на ударениях, реакции слушателя, вторичное движение пружинами, squash & stretch)."""
import math
import numpy as np
from motion import Track, Spring, harden, blink_times, blink_value, viseme_events, mouth_weights, gait_track, FPS
from face import mouth_vec, MOUTH

DEFAULTS = dict(x=0.0, y=0.0, u=150.0, face=1, crouch=0.0, lean=0.0, hip_x=0.0, bob=0.0, jump=0.0,
                head_yaw=0.45, head_tilt=0.0, head_pitch=0.0, neck_lean=0.0,
                arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35, wrist_n=0.0, wrist_f=0.0,
                arm_ik_n=0.0, arm_ik_f=0.0, hx_n=0.5, hy_n=-1.5, hx_f=0.4, hy_f=-1.5,
                brow_up=0.0, brow_inner=0.0, brow_asym=0.0, squint=0.0, wide=0.0, lid=0.0,
                smile=0.25, frown=0.0, look_x=0.3, look_y=0.0, blush=0.0, sx=1.0, sy=1.0,
                walk=1.0, breath=1.0, open_mouth=0.0, tears=0.0, visible=1.0, z=0.0)
DISCRETE = ("hand_n", "hand_f", "mouth_shape", "hold_n", "hold_f", "pose", "face", "visible", "back")


class Actor:
    def __init__(self, name, character, seed=1, extra=None):
        self.name = name
        self.ch = character
        self.seed = seed
        self.tr = {k: Track(v, step=(k in DISCRETE)) for k, v in DEFAULTS.items()}
        for k in DISCRETE:
            if k not in self.tr:
                self.tr[k] = Track(None, step=True)
        self.tr["hand_n"].default = "relax"; self.tr["hand_f"].default = "relax"
        self.lines = []       # (t0, alignment)
        self.forced_blinks = []
        self.extra = extra or {}
        self._gait = None
        self._springs = {"scarf": Spring(40, 5), "hair": Spring(55, 6), "dress": Spring(45, 6)}
        self._prev = None
        self.listen = []      # (t0, t1, actor) — кого слушает (взгляд, кивки)
        self.others = {}
        st = dict(noise=1.0, nod=1.0, bob=1.0, swing=1.0, listen=1.0)
        st.update(self.extra.get("style", {}))
        self.style = st

    # ---- запись ключей
    def k(self, t, e="inout", **vals):
        for name, v in vals.items():
            if name not in self.tr:
                self.tr[name] = Track(0.0)
            self.tr[name].key(t, v, e if name not in DISCRETE else "linear")
        return self

    def say(self, t0, meta):
        self.lines.append((t0, meta["alignment"]))
        self.forced_blinks.append(t0 - 0.05)

    def v(self, name, t):
        return self.tr[name](t)

    # ---- предрасчёт походки и моргания
    def prepare(self, n_frames):
        for tr in self.tr.values():
            harden(tr)
        xs = [self.tr["x"](f / FPS) for f in range(n_frames)]
        self._gait = gait_track(xs, step_px=(self.extra.get("step", 60), self.extra.get("run_step", 105)))
        self._blinks = blink_times(n_frames / FPS, self.seed, self.forced_blinks)
        self._vis = []
        for t0, al in self.lines:
            self._vis += viseme_events(al, t0)
        self._vis.sort()
        self._talk = [(t0 + al["character_start_times_seconds"][0], t0 + al["character_end_times_seconds"][-1]) for t0, al in self.lines]
        self._stress = [s for s, e, v, vow in self._vis if vow and v in ("A", "O", "E")][::2]

    def talking(self, t):
        return any(a - 0.05 <= t <= b + 0.05 for a, b in self._talk)

    # ---- поза кадра
    def pose(self, f):
        t = f / FPS
        T = {k: tr(t) for k, tr in self.tr.items()}
        u = T["u"]
        face = 1 if (T["face"] or 1) >= 0 else -1
        x = T["x"]
        g = self._gait[min(f, len(self._gait) - 1)]
        fnx, fnl, ffx, ffl, ph, sp, runb = g
        walking = sp > 8 and T["walk"] > 0.5
        p = dict(u=u, face=face, x=x, y=T["y"] - T["jump"] - T["z"] * 0)
        # ноги: мировые x стоп -> локальные
        if walking:
            p["foot_n"] = ((fnx - x) * face / u + 0.06, -fnl / u)
            p["foot_f"] = ((ffx - x) * face / u - 0.06, -ffl / u)
            p["foot_ang_n"] = -0.25 * (fnl / 30.0)
            p["foot_ang_f"] = -0.25 * (ffl / 30.0)
        bobw = (0.035 + 0.04 * runb) * abs(math.sin(2 * math.pi * ph)) * self.style["bob"] if walking else 0.0
        # дыхание
        br = math.sin(2 * math.pi * t * (0.28 + 0.25 * self.extra.get("breath_fast", 0))) * 0.012 * T["breath"]
        p["crouch"] = T["crouch"] + bobw * 0.6
        p["bob"] = T["bob"] - br
        p["lean"] = T["lean"] + (0.10 + 0.18 * runb) * (1 if walking else 0)
        p["hip_x"] = T["hip_x"]
        sw = math.sin(2 * math.pi * ph) if walking else 0.0
        amp = (0.35 + 0.55 * runb) * self.style["swing"]
        p["arm_n"] = T["arm_n"] + sw * amp * (1 - T["arm_ik_n"])
        p["arm_f"] = T["arm_f"] - sw * amp * (1 - T["arm_ik_f"])
        p["elbow_n"] = T["elbow_n"] + 0.9 * runb * (1 if walking else 0)
        p["elbow_f"] = T["elbow_f"] + 0.9 * runb * (1 if walking else 0)
        for s in ("n", "f"):
            p["wrist_" + s] = T["wrist_" + s]
            p["arm_ik_" + s] = T["arm_ik_" + s]
            p["hand_t_" + s] = (T["hx_" + s], T["hy_" + s])
            hp = T["hand_" + s]
            p["hand_" + s] = hp if hp else "relax"
            if T.get("hold_" + s):
                p["hold_" + s] = T["hold_" + s]
        # голова: кивки на ударных гласных, лёгкий шум
        nod = sum(0.05 * math.exp(-((t - s0 - 0.05) / 0.08) ** 2) for s0 in self._stress if abs(t - s0) < 0.3) * self.style["nod"]
        noise = (math.sin(t * 1.3 + self.seed) * 0.015 + math.sin(t * 2.9 + self.seed * 2) * 0.01) * self.style["noise"]
        # слушатель: смотрит на говорящего, мягко кивает на его ударениях
        lk_x, lk_w, yaw_b = 0.0, 0.0, 0.0
        if not self.talking(t) and not T.get("back"):
            for t0, t1, other in self.listen:
                if t0 - 0.3 <= t <= t1 + 0.6:
                    w = min(1.0, (t - t0 + 0.3) / 0.35, (t1 + 0.6 - t) / 0.4) * self.style["listen"]
                    dx = (other.tr["x"](t) - x) * face
                    lk_x = max(-0.75, min(0.75, dx / 300.0))
                    yaw_b = 0.12 * (1 if dx > 0 else -1) * min(1.0, abs(dx) / 200)
                    lk_w = max(0.0, w) * (1 - T.get("nolisten", 0.0))
                    nod += 0.5 * sum(0.05 * math.exp(-((t - s0 - 0.22) / 0.1) ** 2) for s0 in other._stress[::2] if abs(t - s0 - 0.2) < 0.35) * self.style["nod"]
                    break
        p["head_yaw"] = T["head_yaw"] + noise * 0.5 + yaw_b * lk_w
        p["head_tilt"] = T["head_tilt"] + noise + (0.03 * sw if walking else 0)
        p["head_pitch"] = T["head_pitch"] + nod * 2
        p["neck_lean"] = T["neck_lean"] + nod * 0.4
        # squash & stretch
        p["sx"], p["sy"] = T["sx"], T["sy"]
        # вторичное движение (пружины): сила от ускорения корня и наклона головы
        if self._prev is None:
            self._prev = (x, 0.0, p["head_tilt"])
        vx = (x - self._prev[0]) * FPS
        ax = (vx - self._prev[1]) * FPS
        dtilt = (p["head_tilt"] - self._prev[2]) * FPS
        self._prev = (x, vx, p["head_tilt"])
        force = -ax * face / u * 0.6 - dtilt * 2.0 + (math.sin(t * 2.1) * 0.6 * self.extra.get("wind", 0))
        p["scarf_sway"] = max(-0.8, min(0.8, self._springs["scarf"].step(force) + self.extra.get("wind_bias", 0) * T.get("wind", 0)))
        p["hair_sway"] = max(-0.8, min(0.8, self._springs["hair"].step(force * 1.2)))
        p["sway"] = max(-0.6, min(0.6, self._springs["dress"].step(force * 0.8)))
        # лицо
        talk = self.talking(t)
        if self._vis and talk:
            mw = mouth_weights(t, self._vis)
        else:
            mw = {"X": 1.0}
        mv = mouth_vec(mw)
        mv = mv.copy()
        mv[3] = mv[3] + T["smile"] * 0.55 - T["frown"] * 0.6
        if T["open_mouth"] > 0:
            mv = mv * (1 - T["open_mouth"]) + np.array(MOUTH[T["mouth_shape"] or "GASP"]) * T["open_mouth"]
        if not talk and T["smile"] > 0.75:
            k = (T["smile"] - 0.75) * 4
            mv = mv * (1 - k) + np.array(MOUTH["SMILE_OPEN"]) * k
        blink = blink_value(t, self._blinks)
        brow_talk = 0.25 * math.exp(-((t - (self._talk[0][0] if self._talk else -9)) / 0.3) ** 2) if self._talk else 0
        lx = T["look_x"] * (1 - lk_w) + lk_x * lk_w
        p["face_st"] = dict(look=(lx, T["look_y"]), blink=blink, squint=T["squint"] + max(0, T["smile"] - 0.6) * 0.6,
                            wide=T["wide"], lid=T["lid"], brow_up=T["brow_up"] + nod * 3 + brow_talk, brow_inner=T["brow_inner"],
                            brow_asym=T["brow_asym"], mouth=mv, blush=T["blush"])
        p["tears"] = T["tears"]
        p["visible"] = T["visible"]
        p["back"] = T.get("back") or 0
        return p
