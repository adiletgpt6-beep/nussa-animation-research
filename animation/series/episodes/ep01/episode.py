"""Серия 1 «Семечко, которое не спешило» (версия 2, семья Самира и Ясмины) — постановка.

Локации: прихожая, кухня, детская, двор и сад (backgrounds/loc_home.py, loc_yard.py) в разном освещении.
Планы: общий, средний, крупный, через плечо, вид со спины, вставки рук и предметов (inserts.py).
Время — в секундах серии. Сцены пишутся по порядку: каждая функция scene_N(E, t) возвращает время конца.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, d) for d in ("engine", "characters", "backgrounds")] + [HERE]
import numpy as np
import skia
from canvas import paint, W, H, gradient_rect, col
from character import Character
from face import mouth_vec
from actor import Actor
from motion import Track, FPS, harden
import samir, yasmina, leyla, hedgehog, props
import loc_yard, loc_home
from home_common import LIGHT
import inserts as I
from script import LINES

DUR = 360.0
YSPOT = loc_yard.SPOT


class Episode:
    def __init__(self, voice_dir):
        self.voice_dir = voice_dir
        self.n_frames = int(DUR * FPS)
        self.S = Actor("samir", Character(samir.DESIGN), seed=2, extra=dict(step=64, run_step=110, style=dict(noise=1.0, nod=1.0, bob=1.1, swing=1.05)))
        self.Y = Actor("yasmina", Character(yasmina.DESIGN), seed=1, extra=dict(step=54, run_step=98, style=dict(noise=1.3, nod=1.25, bob=1.4, swing=1.15)))
        self.L = Actor("leyla", Character(leyla.DESIGN), seed=3, extra=dict(step=60, run_step=88, style=dict(noise=0.55, nod=0.6, bob=0.55, swing=0.55, listen=0.9)))
        self.actors = {"samir": self.S, "yasmina": self.Y, "leyla": self.L}
        for a in self.actors.values():
            a.others = {k: v for k, v in self.actors.items() if v is not a}
        self.cam = {k: Track(v) for k, v in dict(cx=1300.0, cy=640.0, zoom=1.0).items()}
        self.env = {k: Track(v) for k, v in dict(stage=0.0, wind=0.0, rain=0.0, dip=0.0, fade=1.0, water=0.0, soil_hole=0.0, sparkle=0.0,
                                                  stick=0.0, ribbon=0.0, title=0.0, endcard=0.0, sched=0.0, checks=0.0, door=0.0, can_floor=0.0,
                                                  can_x=1500.0).items()}
        self.env["loc"] = Track("hallway:morning", step=True)
        self.hog = {k: Track(v, step=k in ("face", "vis")) for k, v in dict(x=1900.0, y=1050.0, face=-1, sniff=0.0, ball=0.0, vis=0.0).items()}
        self.pigeon = {k: Track(v, step=k in ("face", "vis")) for k, v in dict(x=1800.0, y=1020.0, flap=0.0, peck=0.0, vis=0.0, face=-1).items()}
        self.inserts = []   # (t0, t1, fn(c, t, k))
        self.fx = []        # (t0, t1, kind, params)
        self.sfx = []       # (t, name, gain, pan)
        self.voice = []     # (t, line_id, who)
        self.amb = []       # (t, kind)
        self.meta = {"scene_starts": []}
        self.lines_by_id = {l[0]: l for l in LINES}
        self.layers = {}
        self.cam_ops = []

    # ------------------------------------------------------------ утилиты постановки
    def line(self, lid, t, listeners=None):
        who = self.lines_by_id[lid][2]
        meta = json.load(open(os.path.join(self.voice_dir, lid + ".mp3.json")))
        A = self.actors[who]
        A.say(t, meta)
        self.voice.append((t, lid, who))
        al = meta["alignment"]
        t1 = t + al["character_end_times_seconds"][-1]
        for name, o in self.actors.items():
            if o is A:
                continue
            if listeners is None or name in listeners:
                o.listen.append((t, t1, A))
        return t1

    def jump(self, A, t, **vals):
        for k, v in vals.items():
            if k not in A.tr:
                A.tr[k] = Track(0.0)
            tr = A.tr[k]
            if tr.step:
                tr.key(t, v, "linear")
            else:
                tr.key(t - 1e-3, tr(t - 1e-3), "linear"); tr.key(t, v, "linear")

    def walk(self, A, t0, t1, x, y=None, e="inout"):
        x0 = A.tr["x"](t0)
        A.k(t0, x=x0)
        if y is not None:
            A.k(t0, y=A.tr["y"](t0)).k(t1, y=y, e=e)
        A.k(t1, x=x, e=e)
        if abs(x - x0) > 5:
            A.k(t0, face=1 if x > x0 else -1)

    def cut(self, t, cx, cy, zoom, auto=True):
        self.cam_ops.append(("cut", t, t, cx, cy, zoom, "linear", auto))

    def move(self, t0, t1, cx, cy, zoom, e="inout", auto=True):
        self.cam_ops.append(("move", t0, t1, cx, cy, zoom, e, auto))

    def head(self, A, t):
        p = {k: tr(t) for k, tr in A.tr.items()}
        p["face"] = 1 if (p.get("face") or 1) >= 0 else -1
        for s_ in ("n", "f"):
            p["hand_t_" + s_] = (p["hx_" + s_], p["hy_" + s_])
        J = A.ch.skeleton(p)
        u = p["u"]
        return p["x"] + J["head"][0] * u * p["face"], p["y"] - p["jump"] + J["head"][1] * u, u, p

    def frame(self, t, cx, cy, z):
        """Автокадрирование: головы героев в кадре — на высоте ~40% экрана; крупный план — по центру лица."""
        hw = W / 2 / z
        heads = []
        for A in self.actors.values():
            hx, hy, u, p = self.head(A, t)
            if (p.get("visible") or 0) < 0.5 or p.get("back"):
                continue
            if abs(hx - cx) < hw * 0.92:
                heads.append((hx, hy, u, p["face"]))
        if not heads:
            return cx, cy
        my = sum(h[1] for h in heads) / len(heads)
        ty = my + (0.5 - 0.40) * H / z
        if z < 1.15:
            top, bot = cy - H / 2 / z, cy + H / 2 / z
            if all(top + 0.12 * H / z < h[1] < top + 0.62 * H / z for h in heads):
                ty = cy
        if z >= 1.7:
            near = min(heads, key=lambda h: abs(h[0] - cx))
            cx = near[0] + near[3] * 0.06 * W / z
        elif len(heads) >= 2:
            lo, hi = min(h[0] for h in heads), max(h[0] for h in heads)
            if lo < cx - hw * 0.8 or hi > cx + hw * 0.8:
                cx = (lo + hi) / 2
        return cx, ty

    def resolve_camera(self):
        for kind, t0, t1, cx, cy, z, e, auto in sorted(self.cam_ops, key=lambda o: (o[1], o[0] == "move")):
            if auto:
                cx, cy = self.frame(t1 + (0.35 if kind == "cut" else 0.0), cx, cy, z)
            for k, v in (("cx", cx), ("cy", cy), ("zoom", z)):
                tr = self.cam[k]
                if kind == "cut":
                    tr.key(t0 - 1e-3, tr(t0 - 1e-3), "linear"); tr.key(t0, v, "linear")
                else:
                    tr.key(t0, tr(t0), "linear"); tr.key(t1, v, e)

    def loc(self, t, name, preset, amb):
        self.env["loc"].key(t, f"{name}:{preset}", "linear")
        self.amb.append((t, amb))

    def dip(self, t, half=0.45):
        d = self.env["dip"]
        d.key(t - half, 0.0, "linear"); d.key(t, 1.0, "inout"); d.key(t + half, 0.0, "inout")

    def insert(self, t0, t1, fn):
        self.inserts.append((t0, t1, fn))

    def sfx_at(self, t, name, gain=1.0, pan=0.0):
        self.sfx.append((t, name, gain, pan))

    def envk(self, name, t, v, e="inout"):
        self.env[name].key(t, v, e)

    # ------------------------------------------------------------ рисование
    def get_layers(self, key):
        if key not in self.layers:
            name, preset = key.split(":")
            if name == "yard":
                self.layers[key] = (loc_yard.render_layers(preset), loc_yard.PARALLAX, loc_yard.WW, loc_yard.WH)
            else:
                self.layers[key] = (loc_home.render_layers(name, preset), loc_home.PARALLAX, loc_home.WW, loc_home.WH)
        return self.layers[key]

    def actor_filter(self, preset):
        P = LIGHT[preset]
        L = P["light"]; a = P["amb"]
        r, g, b = [min(1.08, a * (0.78 + 0.22 * c / 255)) for c in L]
        m = [r, 0, 0, 0, 0, 0, g, 0, 0, 0, 0, 0, b, 0, 0, 0, 0, 0, 1, 0]
        return skia.ColorFilters.Matrix(m)

    def draw_frame(self, c, f):
        t = f / FPS
        ins = [x for x in self.inserts if x[0] <= t < x[1]]
        key = self.env["loc"](t)
        preset = key.split(":")[1]
        if ins:
            t0, t1, fn = ins[-1]
            fn(c, t, (t - t0) / max(1e-6, t1 - t0))
        else:
            self.draw_world(c, t, f, key, preset)
        self.grade(c, preset)
        if self.env["title"](t) > 0.01:
            self.title_card(c, self.env["title"](t))
        if self.env["endcard"](t) > 0.01:
            self.end_card(c, self.env["endcard"](t), t)
        dp = self.env["dip"](t)
        if dp > 0.002:
            c.drawRect(skia.Rect(0, 0, W, H), paint((255, 246, 230), dp))
        fd = self.env["fade"](t)
        if fd > 0.002:
            c.drawRect(skia.Rect(0, 0, W, H), paint((12, 10, 18), fd))

    def draw_world(self, c, t, f, key, preset):
        L, PAR, WW, WH = self.get_layers(key)
        P = LIGHT[preset]
        cx, cy, z = self.cam["cx"](t), self.cam["cy"](t), self.cam["zoom"](t)
        z = max(z, 0.9)
        hw, hh = W / 2 / z, H / 2 / z
        cx = min(max(cx, hw), WW - hw)
        cy = min(max(cy, hh), WH - hh)
        blur = min(6.0, max(0.0, (z - 1.55) * 4.0))
        loc = key.split(":")[0]

        def layer(name):
            img = L.get(name)
            if img is None:
                return
            fpar = PAR.get(name, 1.0)
            lcx = cx * fpar + (1 - fpar) * WW / 2
            c.save()
            c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-lcx, -cy)
            pt = skia.Paint()
            b = blur * (1.0 if name != "fg" else 1.6) * (1.0 if name != "main" else 0.8)
            if b > 0.3:
                pt.setImageFilter(skia.ImageFilters.Blur(b, b))
            c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), pt)
            c.restore()

        for nm in ("far", "mid", "main"):
            layer(nm)
        c.save()
        c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
        wind = self.env["wind"](t)
        items = []
        for name, a in self.actors.items():
            p = a.pose(f)
            if p["visible"] > 0.5:
                items.append((p["y"], "actor", (a, p)))
        if loc == "yard":
            items.append((YSPOT[1] + 2, "plant", None))
            if self.env["can_floor"](t) > 0.5:
                items.append((YSPOT[1] + 30, "can", None))
            if self.hog["vis"](t) > 0.5:
                items.append((self.hog["y"](t), "hog", None))
            if self.pigeon["vis"](t) > 0.5:
                items.append((self.pigeon["y"](t), "pigeon", None))
        if loc == "kitchen" and self.env["sched"](t) > 0.5:
            self.fridge_sheet(c, int(self.env["checks"](t)), P)
        flt = self.actor_filter(preset)
        for _, kind, data in sorted(items, key=lambda q: q[0]):
            if kind == "actor":
                a, p = data
                lp = skia.Paint(); lp.setColorFilter(flt)
                c.saveLayer(None, lp)
                a.ch.draw(c, p)
                c.restore()
                if p.get("tears", 0) > 0.05:
                    J = a.ch.skeleton(p)
                    hx = p["x"] + J["head"][0] * p["u"] * p["face"]
                    hy = p["y"] + J["head"][1] * p["u"]
                    props.tears(c, hx + p["face"] * p["u"] * 0.10, hy + p["u"] * 0.06, t, p["tears"])
            elif kind == "plant":
                lit = lambda col_, P_, k=1.0: tuple(min(255, v * P_["amb"] * (0.72 + 0.28 * L_ / 255)) for v, L_ in zip(col_, P_["light"]))
                props.sunflower_pot(c, YSPOT[0], YSPOT[1], self.env["stage"](t), P, lit, wind=wind, t=t, scale=1.45,
                                    sparkle=self.env["sparkle"](t), soil_hole=self.env["soil_hole"](t), water=self.env["water"](t),
                                    pot=False, stick=self.env["stick"](t), ribbon=self.env["ribbon"](t))
            elif kind == "can":
                props.watering_can(0.9)(c, (self.env["can_x"](t), YSPOT[1] + 30 - 90), math.pi / 2, 150)
            elif kind == "hog":
                hg = self.hog
                hedgehog.draw(c, hg["x"](t), hg["y"](t), 110, face=int(hg["face"](t)), sniff=math.sin(t * 9) * hg["sniff"](t),
                              ball=hg["ball"](t), step=hg["x"](t) * 0.08)
            elif kind == "pigeon":
                pg = self.pigeon
                props.pigeon(c, pg["x"](t), pg["y"](t), 64, face=int(pg["face"](t)), flap=abs(math.sin(t * 22)) * pg["flap"](t),
                             peck=max(0, math.sin(t * 8)) * pg["peck"](t))
        for (t0, t1, kind, prm) in self.fx:
            if t0 <= t <= t1:
                getattr(self, "fx_" + kind)(c, t, t0, t1, prm)
        c.restore()
        layer("fg")
        if self.env["rain"](t) > 0.01:
            props.rain(c, t, W, H, self.env["rain"](t) * 0.6, wind=0.3 + wind * 0.3)
        if wind > 0.3:
            props.leaves(c, t, W, H, n=int(8 * wind), wind=wind)

    def fridge_sheet(self, c, checks, P):
        k = P["amb"]
        x0, y0 = 1830, 360
        c.drawRect(skia.Rect(x0 + 4, y0 + 6, x0 + 154, y0 + 116), paint((60, 50, 50), 0.15, blur=5))
        c.drawRect(skia.Rect(x0, y0, x0 + 150, y0 + 110), paint((255, 255, 250)))
        for i in range(7):
            cx = x0 + 14 + i * 19
            c.drawRoundRect(skia.Rect(cx, y0 + 40, cx + 16, y0 + 92), 3, 3, paint((120, 170, 220), style="stroke", width=2))
            if i < checks:
                c.drawCircle(cx + 8, y0 + 80, 5, paint((70, 170, 90)))
        c.drawCircle(x0 + 22, y0 + 20, 12, paint((255, 206, 70)))
        c.drawCircle(x0 + 75, y0 + 4, 9, paint((230, 80, 80)))

    def grade(self, c, preset):
        tint, a = LIGHT[preset]["tint"]
        p = skia.Paint(Color=col(tint, a))
        p.setBlendMode(skia.BlendMode.kSoftLight)
        c.drawRect(skia.Rect(0, 0, W, H), p)
        shader = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), W * 0.78, [col((0, 0, 0), 0.0), col((0, 0, 0), 0.0), col((30, 16, 30), 0.24)], [0.0, 0.62, 1.0])
        vp = skia.Paint(); vp.setShader(shader)
        c.drawRect(skia.Rect(0, 0, W, H), vp)

    def _font(self, size, bold=True):
        f = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        return skia.Font(skia.Typeface.MakeFromFile(f), size)

    def text(self, c, s, x, y, size, color, alpha=1.0, bold=True, outline=None):
        font = self._font(size, bold)
        w = font.measureText(s)
        if outline:
            c.drawString(s, x - w / 2, y, font, paint(outline, alpha, style="stroke", width=size * 0.16))
        c.drawString(s, x - w / 2, y, font, paint(color, alpha))

    def title_card(self, c, k):
        a = min(1.0, k)
        y = 250 + (1 - a) * 30
        self.text(c, "Самир и Ясмина", W / 2, y, 104, (255, 222, 110), a, outline=(120, 70, 50))
        self.text(c, "Семечко, которое не спешило", W / 2, y + 90, 54, (255, 255, 255), a, outline=(80, 60, 70))

    def end_card(self, c, k, t):
        a = min(1, k)
        c.drawRect(skia.Rect(0, 0, W, H), paint((255, 246, 228), a))
        P = LIGHT["day"]
        lit = lambda col_, P_, kk=1.0: col_
        c.save(); c.translate(0, (1 - a) * 60)
        props.sunflower_pot(c, 1460, 1020, 6.0, P, lit, wind=0.15, t=t, scale=1.1, sparkle=0.5 * a, pot=False, stick=1.0, ribbon=1.0)
        hedgehog.draw(c, 1700, 1030, 100, face=-1, sniff=math.sin(t * 8) * 0.6, blink=1.0 if (t % 3.0) < 0.15 else 0.0)
        c.restore()
        rng = np.random.default_rng(4)
        for i in range(12):
            x0, sp, ph = rng.uniform(0, W), rng.uniform(30, 70), rng.uniform(0, 30)
            y = (ph * 40 + t * sp) % (H + 100) - 50
            x = x0 + math.sin(t * 1.3 + ph) * 40
            c.save(); c.translate(x, y); c.rotate(t * 50 + ph * 20)
            c.drawOval(skia.Rect(-14, -6, 14, 6), paint((255, 200, 60), 0.8 * a))
            c.restore()
        self.text(c, "Самир и Ясмина", W / 2 - 260, 470, 104, (236, 160, 50), a, outline=(120, 70, 50))
        self.text(c, "Терпение — это ждать и заботиться", W / 2 - 260, 580, 46, (90, 70, 80), a, bold=False)

    def fx_splash(self, c, t, t0, t1, prm):
        props.splash(c, prm["x"], prm["y"], t - t0, n=prm.get("n", 14), spread=prm.get("spread", 90), seed=prm.get("seed", 1))

    def fx_stream(self, c, t, t0, t1, prm):
        a = prm["actor"]
        p = a.pose(int(t * FPS))
        J = a.ch.skeleton(p)
        hx = p["x"] + J["wr_n"][0] * p["u"] * p["face"]
        hy = p["y"] + J["wr_n"][1] * p["u"]
        props.stream(c, hx + p["face"] * p["u"] * prm.get("dx", 0.8), hy + p["u"] * prm.get("dy", -0.05), prm["tx"], prm["ty"], t)

    def prepare(self):
        self.resolve_camera()
        skip = ("loc", "dip", "fade", "title", "endcard")
        for d in (self.hog, self.pigeon, self.env, self.cam):
            for name, tr in d.items():
                if name not in skip and d is not self.cam:
                    harden(tr)
        for a in self.actors.values():
            a.prepare(self.n_frames)


# ====================================================================== постановка
# Позы-заготовки
def kneel(A, t, side_lean=0.30, dur=0.45):
    A.k(t, crouch=A.tr["crouch"](t), lean=A.tr["lean"](t)).k(t + dur, crouch=0.42, lean=side_lean, e="out")


def stand(A, t, dur=0.45):
    A.k(t, crouch=A.tr["crouch"](t), lean=A.tr["lean"](t)).k(t + dur, crouch=0.0, lean=0.0)


def arms_rest(A, t, dur=0.4):
    A.k(t + dur, arm_ik_n=0.0, arm_ik_f=0.0, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35)


def reach(A, t, side, hx, hy, dur=0.4, hand="grip"):
    A.k(t, **{f"arm_ik_{side}": A.tr[f"arm_ik_{side}"](t)}).k(t + dur, **{f"arm_ik_{side}": 1.0, f"hx_{side}": hx, f"hy_{side}": hy})
    A.k(t + dur * 0.5, **{f"hand_{side}": hand})


def scene_1(E, t):
    """Прихожая и кухня, утро. Хук: Ясмина бежит с полной лейкой — чуть не врезается в Самира с книгой."""
    S, Y, L = E.S, E.Y, E.L
    E.meta["scene_starts"].append(t)
    E.loc(0, "hallway", "morning", "room")
    E.envk("fade", 0, 1.0); E.envk("fade", 0.5, 0.0)
    for A, u in ((S, 140), (Y, 150), (L, 128)):
        A.k(0, u=u, y=1040)
    Y.k(0, x=700, y=1000, face=1, hold_n=props.watering_can(0.9), hand_n="grip", arm_n=0.55, elbow_n=0.5, smile=0.85, look_x=0.5)
    S.k(0, x=2180, y=1060, face=-1, head_yaw=0.3, head_pitch=0.25, look_y=0.6, hold_n=props.book((90, 150, 200)), hand_n="grip",
        arm_n=0.55, elbow_n=1.6, arm_f=0.45, elbow_f=1.5)
    L.k(0, x=2600, y=1000, face=-1, visible=0.0)
    E.cut(0, 1420, 700, 1.05)
    # бег Ясмины и шаги Самира с книгой
    Y.k(0.3, x=700).k(1.55, x=1430, e="out")
    S.k(0.2, x=2180).k(1.6, x=1660, e="inout")
    E.sfx_at(0.3, "slosh", 0.7, -0.3)
    E.sfx_at(0.9, "slosh", 0.6, 0.0)
    # резкая остановка: лейка по инерции, брызги
    Y.k(1.5, lean=0.0).k(1.62, lean=-0.2, e="out").k(1.9, lean=0.06).k(2.2, lean=0.0)
    Y.k(1.5, arm_n=0.55, elbow_n=0.5).k(1.66, arm_n=1.35, elbow_n=0.15, e="out").k(2.3, arm_n=0.4, elbow_n=0.7)
    Y.k(1.62, wide=1.0, brow_up=1.0, smile=0.0, open_mouth=0.5, mouth_shape="GASP").k(2.1, open_mouth=0.0, wide=0.3)
    E.fx.append((1.66, 2.5, "splash", dict(x=1600, y=760, n=16, spread=110, seed=3)))
    E.sfx_at(1.66, "water_splash", 0.75, 0.2)
    # Самир отпрыгивает (сжатие-растяжение), книга вверх
    S.k(1.65, sy=1.0, sx=1.0, jump=0).k(1.74, sy=0.9, sx=1.06, e="out").k(1.86, sy=1.08, sx=0.95, jump=34, e="out").k(2.02, sy=1.0, sx=1.0, jump=0, e="in")
    S.k(2.1, sy=0.95, sx=1.03).k(2.22, sy=1.0, sx=1.0)
    S.k(1.68, head_pitch=0.25, look_y=0.6, wide=0.0).k(1.8, head_pitch=-0.05, look_y=0.0, look_x=0.4, wide=1.0, brow_up=1.0, open_mouth=0.5, mouth_shape="GASP")
    S.k(1.8, arm_n=1.1, elbow_n=1.0).k(2.5, arm_n=0.75, elbow_n=1.6)
    S.k(2.2, open_mouth=0.0, wide=0.3)
    E.sfx_at(1.8, "jump_whoosh", 0.35, 0.3)
    E.cut(1.95, 1540, 600, 1.55)
    t = E.line("s1_01", 2.0)
    S.k(2.4, brow_inner=-0.2, frown=0.25, smile=0.0).k(t, brow_inner=0.0)
    # Ясмина — крупно: смущённая улыбка, прячет лейку за спину
    t0 = t + 0.25
    E.cut(t0, 1440, 560, 2.1)
    Y.k(t0, look_x=0.6, head_tilt=0.0).k(t0 + 0.4, smile=0.9, squint=0.6, head_tilt=-0.12, brow_inner=0.4, blush=0.6, arm_n=0.05, elbow_n=0.2)
    t = E.line("s1_02", t0 + 0.1)
    Y.k(t - 1.0, hip_x=-0.03).k(t - 0.5, hip_x=0.03).k(t, hip_x=0.0, blush=0.2)
    # через плечо Ясмины: Самир спрашивает
    t0 = t + 0.2
    E.jump(Y, t0, back=1, u=215, y=1250, x=1230)
    E.cut(t0, 1640, 560, 1.45)
    S.k(t0, frown=0.0, brow_inner=0.0, smile=0.25, head_tilt=0.08, brow_asym=0.5, arm_f=0.35, elbow_f=0.6, hand_f="open")
    t = E.line("s1_03", t0 + 0.15)
    S.k(t - 1.5, arm_f=0.9, elbow_f=0.4).k(t, arm_f=0.45, elbow_f=1.5, hand_f="grip")
    # мама в дверях кухни, с полотенцем
    t0 = t + 0.2
    E.jump(Y, t0, back=0, u=150, y=1000, x=1430)
    Y.k(t0, face=1, arm_n=0.4, elbow_n=0.7)
    E.jump(L, t0, visible=1.0, x=2150, y=980)
    L.k(t0, face=-1, hold_n=props.towel(), hand_n="grip", arm_n=0.5, elbow_n=1.4, smile=0.6, look_x=0.5, head_yaw=0.3)
    E.cut(t0, 1800, 640, 1.08)
    for A in (S, Y):
        A.k(t0 + 0.1, head_yaw=A.tr["head_yaw"](t0)).k(t0 + 0.45, look_x=0.7)
    S.k(t0 + 0.3, face=1)
    t = E.line("s1_04", t0 + 0.5)
    E.walk(L, t, t + 2.2, 1910)
    L.k(t + 2.3, hold_n=None, hand_n="relax", arm_n=0.12, elbow_n=0.35)
    E.sfx_at(t + 2.25, "cloth", 0.35, 0.3)
    Y.k(t + 1.7, face=1)
    E.move(t, t + 2.4, 1700, 660, 1.2)
    # мама приседает к детям, раскрывает ладонь
    t0 = t + 2.5
    L.k(t0, crouch=0.0).k(t0 + 0.7, crouch=0.55, lean=0.18, e="inout")
    L.k(t0 + 0.4, arm_n=0.9, elbow_n=0.6, hand_n="open", wrist_n=-0.4)
    S.k(t0 + 0.4, x=1640, face=1).k(t0 + 1.0, crouch=0.15, lean=0.15)
    Y.k(t0 + 0.5, crouch=0.1, lean=0.2, look_y=0.3)
    E.cut(t0, 1760, 700, 1.35)
    t = E.line("s1_05", t0 + 0.6)
    E.insert(t - 3.4, t + 0.6, lambda c, tt, k: I.palm_seed(c, tt, k))
    E.sfx_at(t - 2.0, "sparkle", 0.35, 0.0)
    # Ясмина — крупно: «Чудо? Настоящее?!» — руки к щекам
    t0 = t + 0.6
    E.cut(t0, 1610, 560, 2.2)
    Y.k(t0, wide=1.0, brow_up=1.0, smile=0.9, arm_ik_n=1.0, arm_ik_f=1.0, hx_n=0.22, hy_n=-1.95, hx_f=-0.05, hy_f=-1.95, hand_n="open", hand_f="open")
    t = E.line("s1_06", t0 + 0.1)
    Y.k(t - 0.6, jump=0).k(t - 0.35, jump=22, sy=1.06, sx=0.96, e="out").k(t - 0.1, jump=0, sy=1.0, sx=1.0, e="in")
    Y.k(t + 0.3, arm_ik_n=0.0, arm_ik_f=0.0, wide=0.3)
    # Самир с лупой — смешной огромный глаз
    t0 = t + 0.3
    S.k(t0, hold_n=props.magnifier(), hand_n="grip")
    E.insert(t0, t0 + 1.7, lambda c, tt, k: I.magnifier_eye(c, tt, k, dict(face=1, head_yaw=0.12, face_st=dict(mouth=mouth_vec({"O": 0.7, "SMILE_OPEN": 0.3}), brow_up=0.9, wide=0.6, look=(0.0, 0.2)))))
    E.sfx_at(t0 + 0.2, "boing", 0.25, 0.0)
    t0 += 1.7
    E.cut(t0, 1720, 600, 1.7)
    S.k(t0, crouch=0.15, lean=0.25, arm_n=1.2, elbow_n=1.6, hand_n="grip", brow_up=0.4, look_y=0.4)
    t = E.line("s1_07", t0 + 0.1)
    S.k(t - 0.8, lean=0.0, crouch=0.0, brow_asym=0.6, smile=0.1, arm_n=0.4, elbow_n=1.2)
    # мама — улыбка с хитринкой
    E.cut(t + 0.2, 1830, 560, 1.9)
    L.k(t + 0.2, smile=0.8, squint=0.5, head_tilt=0.1)
    t = E.line("s1_08", t + 0.35)
    L.k(t + 0.2, hand_n="relax", arm_n=0.4, elbow_n=0.8)
    # Ясмина берёт семечко и бежит к двери
    t0 = t + 0.4
    E.cut(t0, 1500, 660, 1.05)
    Y.k(t0, crouch=0.0, lean=0.0, arm_n=0.9, elbow_n=0.6, hand_n="open").k(t0 + 0.4, arm_n=0.5, elbow_n=1.4, hand_n="fist", smile=1.0)
    L.k(t0 + 0.5, crouch=0.0, lean=0.0)
    Y.k(t0 + 0.6, face=-1)
    E.walk(Y, t0 + 0.7, t0 + 2.4, 420, e="in")
    E.line("r_yas_giggle", t0 + 0.8, listeners=[])
    S.k(t0 + 1.0, face=-1, hold_n=None, hand_n="relax", arm_n=0.12, elbow_n=0.35)
    E.walk(S, t0 + 1.1, t0 + 2.8, 560)
    E.move(t0 + 0.8, t0 + 2.6, 900, 660, 1.0)
    E.sfx_at(t0 + 2.3, "door_open", 0.7, -0.6)
    E.dip(t0 + 3.0)
    return t0 + 3.0


def scene_2(E, t):
    """Двор, утро: посадка с «Бисмиллях», полив, ожидание, юмор «А за две?»."""
    S, Y, L = E.S, E.Y, E.L
    E.meta["scene_starts"].append(t)
    E.loc(t, "yard", "morning", "yard_morning")
    dx, dy = loc_yard.DOOR
    E.jump(Y, t, x=dx - 40, y=840, face=-1, crouch=0.0, lean=0.0, arm_n=0.5, elbow_n=1.4, hand_n="fist", u=150)
    E.jump(S, t, x=dx + 60, y=835, face=-1, u=140, crouch=0.0, lean=0.0, hold_n=props.watering_can(0.9), hand_n="grip", arm_n=0.35, elbow_n=0.5)
    E.jump(L, t, x=dx + 120, y=830, face=-1, visible=0.0, crouch=0.0, lean=0.0, u=128)
    # общий план двора, название серии
    E.cut(t, 2000, 600, 0.9)
    E.envk("title", t + 0.3, 0.0, "linear"); E.envk("title", t + 1.0, 1.0); E.envk("title", t + 3.6, 1.0); E.envk("title", t + 4.3, 0.0)
    E.walk(Y, t + 0.5, t + 3.6, 1490, y=1075)
    E.walk(S, t + 0.9, t + 4.3, 1760, y=1090)
    E.move(t + 0.5, t + 4.6, 1650, 720, 1.05)
    E.sfx_at(t + 0.2, "door_close", 0.4, 0.6)
    # Ясмина опускается на колени у грядки
    t0 = t + 3.8
    Y.k(t0, face=1)
    kneel(Y, t0 + 0.1, 0.32)
    E.envk("soil_hole", t0, 0.0); E.envk("soil_hole", t0 + 1.0, 1.0)
    reach(Y, t0 + 0.2, "n", 0.6, -0.55, hand="grip")
    for i in range(3):
        tt = t0 + 0.6 + i * 0.35
        Y.k(tt, hy_n=-0.5).k(tt + 0.17, hy_n=-0.38).k(tt + 0.34, hy_n=-0.5)
        E.sfx_at(tt + 0.15, "dig", 0.5, 0.0)
    E.cut(t0, 1560, 860, 1.6)
    # вставка: пальчик кладёт семечко, «Бисмиллях. Расти, семечко»
    t0 += 1.8
    E.insert(t0, t0 + 4.2, lambda c, tt, k: I.plant_seed(c, tt, k))
    E.sfx_at(t0 + 1.5, "seed_drop", 0.5, 0.0)
    E.sfx_at(t0 + 2.4, "pat_soil", 0.6, 0.0); E.sfx_at(t0 + 3.0, "pat_soil", 0.5, 0.0)
    E.line("s2_01", t0 + 0.3)
    E.envk("soil_hole", t0 + 4.0, 1.0); E.envk("soil_hole", t0 + 4.2, 0.0, "linear")
    # Самир подаёт лейку; Ясмина поливает — вставка капель
    t0 += 4.2
    E.cut(t0, 1640, 760, 1.35)
    S.k(t0, crouch=0.15, lean=0.2, arm_n=1.1, elbow_n=0.3)
    Y.k(t0 + 0.5, arm_ik_n=0.0, arm_n=0.8, elbow_n=0.5).k(t0 + 0.8, hold_n=props.watering_can(0.9), hand_n="grip")
    S.k(t0 + 0.8, hold_n=None, hand_n="relax", arm_n=0.3, elbow_n=0.4, crouch=0.0, lean=0.0, smile=0.5)
    E.insert(t0 + 1.3, t0 + 4.6, lambda c, tt, k: I.drops(c, tt, t0 + 1.3, k))
    E.sfx_at(t0 + 1.4, "drips", 0.9, 0.0); E.sfx_at(t0 + 2.6, "drips", 0.8, 0.0)
    E.envk("water", t0 + 1.3, 0.0); E.envk("water", t0 + 4.6, 1.0)
    # пауза без слов: Ясмина ждёт, подперев щёки; птичка, медленный наезд
    t0 += 4.6
    E.cut(t0, 1560, 840, 1.3)
    Y.k(t0, hold_n=None, hand_n="relax", arm_n=0.12, elbow_n=0.35)
    E.envk("can_floor", t0 - 0.01, 0.0, "linear"); E.envk("can_floor", t0, 1.0, "linear"); E.envk("can_x", t0, 1400.0, "linear")
    Y.k(t0 + 0.3, arm_ik_n=1.0, arm_ik_f=1.0, hx_n=0.18, hy_n=-1.55, hx_f=0.0, hy_f=-1.55, hand_n="fist", hand_f="fist", look_x=0.6, look_y=0.6, head_pitch=0.25)
    E.pigeon["vis"].key(t0 + 0.8, 1, "linear"); E.pigeon["x"].key(t0 + 0.8, 1900.0, "linear").key(t0 + 2.6, 1760.0)
    E.pigeon["y"].key(t0 + 0.8, 1010.0, "linear"); E.pigeon["peck"].key(t0 + 1.0, 0.0).key(t0 + 1.5, 1.0).key(t0 + 2.4, 1.0).key(t0 + 2.8, 0.0)
    E.pigeon["vis"].key(t0 + 3.6, 0, "linear")
    E.pigeon["flap"].key(t0 + 3.0, 0.0).key(t0 + 3.2, 1.0)
    E.pigeon["x"].key(t0 + 3.6, 2300.0, "in"); E.pigeon["y"].key(t0 + 3.6, 700.0, "in")
    E.sfx_at(t0 + 1.0, "coo", 0.35, 0.4); E.sfx_at(t0 + 3.1, "wings", 0.4, 0.5)
    Y.k(t0 + 2.0, lean=0.32).k(t0 + 3.8, lean=0.55, head_pitch=0.35, e="inout")       # всё ближе к земле
    E.move(t0, t0 + 4.0, 1560, 900, 1.9)
    # «Ну-у? И где же чудо?»
    t0 += 4.2
    Y.k(t0, lean=0.3, head_pitch=0.0, look_y=0.0, frown=0.4, brow_inner=-0.4, arm_ik_n=0.0, arm_ik_f=0.0, arm_n=0.6, elbow_n=1.6, arm_f=0.5, elbow_f=1.6)
    t = E.line("s2_02", t0 + 0.2)
    # Самир смеётся
    E.cut(t + 0.2, 1680, 720, 1.4)
    S.k(t + 0.2, smile=0.9, squint=0.5, head_tilt=-0.1)
    t = E.line("s2_03", t + 0.3)
    S.k(t - 1.6, lean=-0.06, arm_f=0.4, elbow_f=1.9).k(t, lean=0.0)
    # Ясмина — крупно, с надеждой
    E.cut(t + 0.2, 1480, 830, 2.2)
    Y.k(t + 0.2, frown=0.0, brow_inner=0.5, brow_up=0.6, smile=0.4, wide=0.4, look_x=0.7, look_y=-0.4, head_tilt=0.12)
    t = E.line("s2_04", t + 0.35)
    tl = E.line("r_samir_laugh", t + 0.25, listeners=["yasmina"])
    S.k(t + 0.2, smile=1.0, squint=0.8, lean=-0.1, head_pitch=-0.1).k(tl + 0.3, lean=0.0, head_pitch=0.0)
    E.cut(t + 0.2, 1620, 760, 1.3)
    # Ясмина хватает лейку — Самир мягко останавливает
    t0 = tl + 0.3
    Y.k(t0, crouch=0.42).k(t0 + 0.5, crouch=0.2, lean=0.25, arm_n=0.9, elbow_n=0.4, hand_n="grip", e="out")
    E.envk("can_floor", t0 + 0.5, 1.0, "linear"); E.envk("can_floor", t0 + 0.51, 0.0, "linear")
    Y.k(t0 + 0.51, hold_n=props.watering_can(0.9)).k(t0 + 0.9, arm_n=1.4, elbow_n=0.1)
    E.walk(S, t0 + 0.4, t0 + 0.9, 1640)
    S.k(t0 + 0.9, face=-1, arm_n=1.3, elbow_n=0.3, hand_n="open", wide=0.7, brow_up=0.7)
    t = E.line("s2_05", t0 + 0.9)
    Y.k(t0 + 1.4, arm_n=0.9, elbow_n=0.5)
    S.k(t - 2.0, arm_n=0.6, elbow_n=1.2, hand_n="point", wide=0.0, brow_up=0.3)
    S.k(t + 0.6, arm_n=0.12, elbow_n=0.35, hand_n="relax", smile=0.4)
    # вздох: плечи опускаются; мама улыбается с крыльца
    t0 = t + 0.2
    E.cut(t0, 1540, 800, 1.9)
    Y.k(t0, crouch=0.15, lean=0.1, brow_inner=0.7, frown=0.2, smile=0.0, head_tilt=-0.15, arm_n=0.2, elbow_n=0.4).k(t0 + 1.2, bob=0.05)
    t = E.line("s2_06", t0 + 0.2)
    Y.k(t, bob=0.0)
    E.jump(L, t + 0.2, visible=1.0)
    L.k(t + 0.2, smile=0.75, squint=0.4, head_tilt=0.08, arm_n=0.3, elbow_n=1.3, arm_f=-0.3, elbow_f=1.3)
    E.cut(t + 0.2, 2400, 700, 1.0)
    E.dip(t + 2.6)
    return t + 2.6


def scene_3(E, t):
    """Детская → вечер во дворе: Ясмина выкапывает семечко, слёзы, мама объясняет про корни, брат помогает."""
    S, Y, L = E.S, E.Y, E.L
    E.meta["scene_starts"].append(t)
    E.loc(t, "kidsroom", "golden", "room")
    # Ясмина у окна, со спины — смотрит на сад (без слов)
    E.jump(Y, t, x=1300, y=1000, face=1, back=1, u=165, crouch=0.0, lean=0.0, hold_n=None, hand_n="relax", arm_n=0.3, elbow_n=0.9, arm_f=-0.3, elbow_f=0.9,
           brow_inner=0.0, frown=0.0, smile=0.2, head_tilt=0.0, arm_ik_n=0.0, arm_ik_f=0.0)
    E.jump(S, t, visible=0.0, x=300); E.jump(L, t, visible=0.0, x=300)
    E.cut(t, 1300, 560, 1.15, auto=False)
    E.move(t, t + 4.5, 1300, 500, 1.4, auto=False)
    Y.k(t + 1.5, hip_x=-0.03).k(t + 2.6, hip_x=0.03).k(t + 3.4, hip_x=0.0)
    tl = E.line("r_yas_sigh", t + 3.0, listeners=[])
    t0 = tl + 0.4
    E.dip(t0 + 0.2, 0.35)
    # двор вечером
    t0 += 0.2
    E.loc(t0, "yard", "golden", "yard_evening")
    dx, dy = loc_yard.DOOR
    E.jump(Y, t0, back=0, u=150, x=1250, y=1085, face=1, crouch=0.12, lean=0.12, arm_n=-0.6, elbow_n=0.9, arm_f=0.5, elbow_f=0.9)
    E.jump(S, t0, visible=1.0, x=dx, y=840, face=-1, u=140, crouch=0.0, lean=0.0, hold_n=None, smile=0.2)
    E.jump(L, t0, visible=1.0, x=dx + 200, y=830, face=-1, u=128, crouch=0.0, lean=0.0, smile=0.3)
    E.envk("stage", t0, 0.0); E.envk("water", t0, 0.6); E.envk("water", t0 + 1, 0.2)
    E.cut(t0, 1500, 820, 1.25)
    # на цыпочках, оглядывается
    E.walk(Y, t0 + 0.3, t0 + 2.6, 1490, e="inout")
    Y.k(t0 + 0.8, head_yaw=-0.5, look_x=-0.8).k(t0 + 1.4, head_yaw=0.45, look_x=0.5).k(t0 + 2.0, head_yaw=-0.4, look_x=-0.7).k(t0 + 2.6, head_yaw=0.4, look_x=0.4)
    Y.k(t0 + 2.6, face=1)
    t = E.line("s3_01", t0 + 2.9, listeners=[])
    kneel(Y, t - 0.8)
    Y.k(t - 0.6, frown=0.2, brow_inner=0.5, look_y=0.5)
    reach(Y, t + 0.1, "n", 0.6, -0.55)
    E.envk("soil_hole", t + 0.1, 0.0)
    for i in range(4):
        tt = t + 0.4 + i * 0.32
        Y.k(tt, hy_n=-0.5).k(tt + 0.16, hy_n=-0.38).k(tt + 0.32, hy_n=-0.5)
        E.sfx_at(tt + 0.12, "dig", 0.55, 0.0)
    E.envk("soil_hole", t + 1.6, 1.0)
    E.move(t, t + 1.6, 1540, 860, 1.7)
    # Самир с крыльца: «Ясми, не надо!»
    t0 = t + 1.1
    E.cut(t0, 2500, 720, 1.25)
    S.k(t0, wide=0.8, brow_up=0.8, smile=0.0, arm_n=1.4, elbow_n=0.3, hand_n="open")
    t = E.line("s3_02", t0 + 0.15, listeners=[])
    E.walk(S, t, t + 1.8, 1760, y=1090)
    S.k(t + 1.9, arm_n=0.12, elbow_n=0.35, hand_n="relax", wide=0.2, brow_up=0.2, brow_inner=0.4)
    # находка: «у него хвостик… я его сломала!»
    t0 = t + 0.3
    E.cut(t0, 1500, 820, 2.0)
    Y.k(t0, arm_ik_n=0.0, arm_n=1.25, elbow_n=1.4, hand_n="pinch", hold_n=props.seed(1.0), lean=0.15, look_x=0.4, look_y=-0.4, wide=0.6, brow_up=0.6)
    t = E.line("s3_03", t0 + 0.3, listeners=["samir"])
    Y.k(t - 1.8, wide=0.0, brow_up=0.0, brow_inner=1.0, frown=0.6, open_mouth=0.0).k(t - 0.6, tears=1.0, mouth_shape="CRY", open_mouth=0.5)
    Y.k(t + 0.6, open_mouth=0.3)
    # мама подходит плавно, опускается рядом, обнимает
    t0 = t + 0.3
    E.cut(t0, 1700, 760, 1.2)
    E.walk(L, t0 - 1.5, t0 + 1.4, 1300, y=1072)
    L.k(t0 + 1.5, face=1)
    L.k(t0 + 1.5, crouch=0.0).k(t0 + 2.2, crouch=0.42, lean=0.12)
    L.k(t0 + 1.6, arm_n=1.0, elbow_n=0.9, hand_n="open", arm_f=0.8, elbow_f=0.9, hand_f="open", smile=0.5, brow_inner=0.4, head_tilt=0.12)
    t = E.line("s3_04", t0 + 1.8)
    Y.k(t - 0.4, face=-1, head_yaw=0.4)
    E.walk(Y, t, t + 0.6, 1460)
    Y.k(t + 0.1, crouch=0.2, lean=0.1)
    L.k(t + 0.4, arm_n=0.6, elbow_n=1.8, arm_f=0.5, elbow_f=1.9, hand_n="relax", hand_f="relax", look_x=0.4, look_y=0.4)
    E.cut(t + 0.2, 1440, 720, 1.7)
    # ладонь мамы с семечком и корешком
    t0 = t + 0.6
    t = E.line("s3_05", t0)
    E.insert(t0 - 0.1, t - 1.4, lambda c, tt, k: I.palm_seed(c, tt, k, root=1.0, evening=True))
    Y.k(t0, tears=0.6, hold_n=None, arm_n=0.4, elbow_n=1.4)
    E.cut(t - 1.4, 1420, 700, 2.0)
    L.k(t - 1.4, smile=0.7, brow_inner=0.2)
    # Ясмина всхлипывает
    E.cut(t + 0.2, 1450, 740, 2.3)
    Y.k(t + 0.2, tears=0.4, brow_inner=0.8, frown=0.2, look_x=-0.5, look_y=-0.4, head_tilt=0.15)
    t = E.line("s3_06", t + 0.35)
    # мама объясняет: разрез земли — корешок растёт вниз
    t0 = t + 0.25
    E.cut(t0, 1440, 700, 1.6)
    t = E.line("s3_07", t0)
    E.insert(t0 + 1.0, t - 0.8, lambda c, tt, k: I.root_section(c, tt, k))
    E.sfx_at(t0 + 1.3, "sparkle", 0.2, 0.0)
    Y.k(t - 0.8, tears=0.0, brow_inner=0.3, wide=0.3, look_y=-0.3)
    # Самир: «Как фундамент у дома!»
    E.cut(t + 0.2, 1700, 700, 1.6)
    S.k(t + 0.2, face=-1, smile=0.8, wide=0.5, brow_up=0.7, arm_n=1.6, elbow_n=0.6, arm_f=1.4, elbow_f=0.6, hand_n="open", hand_f="open")
    t = E.line("s3_08", t + 0.3)
    S.k(t + 0.3, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35, hand_n="relax", hand_f="relax")
    # мама — крупно: «Терпение — это ждать и заботиться»
    E.cut(t + 0.2, 1390, 590, 2.1)
    L.k(t + 0.2, smile=0.6, squint=0.3, look_x=0.5, look_y=0.4, head_tilt=0.1)
    t = E.line("s3_09", t + 0.4)
    # «А если я не умею ждать?»
    E.cut(t + 0.2, 1450, 730, 2.3)
    Y.k(t + 0.2, look_x=-0.6, look_y=-0.5, brow_inner=0.6, smile=0.0, head_tilt=0.1)
    t = E.line("s3_10", t + 0.4)
    # «Тогда будем учиться вместе…» — объятие
    E.cut(t + 0.2, 1420, 660, 1.75)
    L.k(t + 0.2, arm_n=0.5, elbow_n=2.0, arm_f=0.4, elbow_f=2.0, smile=0.8, squint=0.5)
    Y.k(t + 0.2, face=-1, smile=0.5, brow_inner=0.2, head_tilt=-0.15, blink=0)
    t = E.line("s3_11", t + 0.45)
    # Самир опускается рядом: «Давай посадим его обратно. Вместе.»
    t0 = t + 0.3
    E.cut(t0, 1580, 780, 1.4)
    E.walk(S, t0 - 0.5, t0 + 0.5, 1660)
    S.k(t0 + 0.5, face=-1)
    kneel(S, t0 + 0.6, 0.25)
    S.k(t0 + 0.6, smile=0.7, brow_inner=0.3, head_tilt=0.12)
    t = E.line("s3_12", t0 + 0.7)
    Y.k(t + 0.2, face=1, smile=0.8, tears=0.0)
    E.insert(t + 0.4, t + 3.6, lambda c, tt, k: I.plant_seed(c, tt, k, two_hands=True))
    E.sfx_at(t + 1.9, "pat_soil", 0.6, 0.0); E.sfx_at(t + 2.5, "pat_soil", 0.5, 0.0)
    E.envk("soil_hole", t + 3.5, 0.0, "linear")
    # тихий общий план: втроём у грядки на закате
    t0 = t + 3.6
    E.cut(t0, 1550, 620, 0.95)
    E.move(t0, t0 + 3.6, 1560, 600, 1.05)
    L.k(t0, crouch=0.42, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35)
    Y.k(t0, crouch=0.42, lean=0.1, face=1, look_x=0.5, look_y=0.4)
    E.dip(t0 + 3.8)
    return t0 + 3.8


def scene_4(E, t):
    """Кухня: расписание. Дни ожидания: кружка воды, голубь, ёжик, росток!"""
    S, Y, L = E.S, E.Y, E.L
    E.meta["scene_starts"].append(t)
    E.loc(t, "kitchen", "morning", "room")
    E.jump(S, t, visible=1.0, x=1780, y=1060, face=1, u=140, crouch=0.0, lean=0.0, back=0, hold_n=None, hand_n="open", arm_n=1.9, elbow_n=0.5, smile=0.7)
    E.jump(Y, t, visible=1.0, x=1450, y=1070, face=1, u=150, crouch=0.0, lean=0.0, tears=0.0, hold_n=props.cup((240, 150, 120)), hand_n="grip",
           arm_n=0.5, elbow_n=1.3, smile=0.7, brow_inner=0.0, frown=0.0)
    E.jump(L, t, visible=1.0, x=2260, y=1000, face=-1, u=128, crouch=0.0, lean=0.0, smile=0.6, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35, hand_n="relax", hand_f="relax")
    E.envk("sched", t, 0.0, "linear"); E.envk("sched", t + 0.6, 1.0, "linear")
    E.cut(t, 1760, 640, 1.2)
    E.sfx_at(t + 0.55, "click", 0.6, 0.3)
    E.sfx_at(t + 0.3, "paper", 0.5, 0.3)
    S.k(t + 0.9, face=-1, arm_n=0.9, elbow_n=0.4, hand_n="point")
    t1 = E.line("s4_01", t + 0.9)
    E.insert(t + 2.0, t1 + 0.2, lambda c, tt, k: I.schedule(c, tt, 0.0, 0))
    E.cut(t1 + 0.2, 1560, 560, 1.9)
    Y.k(t1 + 0.2, smile=1.0, squint=0.6, arm_f=2.6, elbow_f=0.6, hand_f="open", head_tilt=0.1)   # «салют»
    t = E.line("s4_02", t1 + 0.3)
    Y.k(t + 0.4, arm_f=-0.12, elbow_f=0.35, hand_f="relax")
    E.dip(t + 0.8, 0.35)
    # монтаж дней (двор, утро): одна кружка — и галочка
    t0 = t + 0.8
    E.loc(t0, "yard", "morning", "yard_morning")
    E.jump(Y, t0, x=1500, y=1075, face=1, crouch=0.2, lean=0.2, hold_n=props.cup((240, 150, 120)), hand_n="grip", arm_n=0.9, elbow_n=0.5, smile=0.7)
    E.jump(S, t0, visible=0.0); E.jump(L, t0, visible=0.0)
    E.envk("water", t0, 0.0)
    E.cut(t0, 1560, 860, 1.6)
    Y.k(t0 + 0.6, arm_n=1.2, elbow_n=0.2, wrist_n=-0.9)
    E.fx.append((t0 + 0.8, t0 + 1.8, "stream", dict(actor=Y, tx=YSPOT[0], ty=YSPOT[1] - 14, dx=0.5, dy=-0.1)))
    E.sfx_at(t0 + 0.8, "pour_small", 0.7, 0.0)
    E.envk("water", t0 + 0.8, 0.0); E.envk("water", t0 + 1.8, 1.0)
    Y.k(t0 + 2.0, wrist_n=0.0, arm_n=0.6, elbow_n=0.9)
    E.insert(t0 + 2.3, t0 + 3.6, lambda c, tt, k: I.schedule(c, tt, k, 1))
    E.sfx_at(t0 + 2.6, "scribble", 0.6, 0.0)
    # голубь: «Кыш, голубь! Это не тебе!»
    t0 += 3.6
    E.jump(Y, t0, x=1420, crouch=0.0, lean=0.0, hold_n=None, hand_n="relax", arm_n=0.12, elbow_n=0.35, wrist_n=0.0)
    E.pigeon["vis"].key(t0, 1, "linear"); E.pigeon["x"].key(t0 - 0.01, 1700.0, "linear").key(t0 + 0.6, 1640.0)
    E.pigeon["y"].key(t0, 1010.0, "linear"); E.pigeon["face"].key(t0, -1, "linear")
    E.pigeon["peck"].key(t0 + 0.4, 0.0).key(t0 + 0.7, 1.0)
    E.cut(t0, 1560, 800, 1.45)
    E.sfx_at(t0 + 0.3, "coo", 0.45, 0.3)
    Y.k(t0 + 0.5, wide=0.6, brow_up=0.3, frown=0.3)
    t = E.line("s4_03", t0 + 0.8, listeners=[])
    for i in range(3):
        tt = t0 + 0.9 + i * 0.35
        Y.k(tt, arm_n=2.4, arm_f=2.2, elbow_n=0.3, elbow_f=0.3, hand_n="open", hand_f="open").k(tt + 0.17, arm_n=1.7, arm_f=1.5)
    Y.k(t + 0.3, arm_n=0.12, arm_f=-0.12, elbow_n=0.35, elbow_f=0.35, frown=0.0, wide=0.0, smile=0.5)
    E.pigeon["peck"].key(t - 0.6, 0.0); E.pigeon["flap"].key(t - 0.6, 0.0).key(t - 0.4, 1.0)
    E.pigeon["x"].key(t - 0.5, 1640.0).key(t + 0.6, 2200.0, "in"); E.pigeon["y"].key(t - 0.5, 1010.0).key(t + 0.6, 650.0, "in")
    E.pigeon["vis"].key(t + 0.7, 0, "linear")
    E.sfx_at(t - 0.5, "wings", 0.5, 0.5)
    # ёжик Колючкин нюхает грядку
    t0 = t + 0.9
    E.hog["vis"].key(t0, 1, "linear"); E.hog["x"].key(t0 - 0.01, 1900.0, "linear").key(t0 + 1.6, 1660.0)
    E.hog["y"].key(t0, 1030.0, "linear"); E.hog["sniff"].key(t0 + 1.4, 0.0).key(t0 + 1.8, 1.0)
    E.sfx_at(t0 + 1.7, "sniff", 0.5, 0.3)
    E.cut(t0, 1600, 820, 1.5)
    Y.k(t0 + 1.4, look_x=0.7, look_y=0.5, smile=0.8, squint=0.3, brow_up=0.4)
    t = E.line("s4_04", t0 + 1.9, listeners=[])
    Y.k(t - 1.6, arm_n=1.0, elbow_n=0.6, hand_n="point").k(t + 0.2, arm_n=0.12, elbow_n=0.35, hand_n="relax")
    E.hog["ball"].key(t - 0.8, 0.0).key(t - 0.5, 1.0, "out").key(t + 0.9, 1.0).key(t + 1.2, 0.0)
    E.sfx_at(t - 0.6, "hog_huff", 0.45, 0.3)
    E.hog["x"].key(t + 1.3, 1660.0).key(t + 2.6, 2100.0); E.hog["face"].key(t + 1.25, 1, "linear")
    E.hog["vis"].key(t + 2.7, 0, "linear")
    E.dip(t + 2.4, 0.35)
    # утро: росток!
    t0 = t + 2.4
    E.envk("stage", t0 - 0.1, 0.0, "linear"); E.envk("stage", t0, 1.0, "linear")
    E.jump(Y, t0, x=1450, crouch=0.0, lean=0.0, arm_n=0.12, elbow_n=0.35, smile=0.4, face=1)
    E.insert(t0, t0 + 3.4, lambda c, tt, k: I.sprout(c, tt, min(1.0, k * 1.3)))
    E.sfx_at(t0 + 0.9, "pop_soft", 0.6, 0.0); E.sfx_at(t0 + 1.8, "sparkle", 0.35, 0.0)
    t0 += 3.4
    E.cut(t0, 1500, 760, 1.25)
    Y.k(t0, wide=1.0, brow_up=1.0, smile=1.0, crouch=0.15).k(t0 + 0.3, crouch=0.0, jump=60, sy=1.08, sx=0.94, e="out").k(t0 + 0.6, jump=0, sy=1.0, sx=1.0, e="in")
    Y.k(t0 + 0.4, arm_n=2.6, arm_f=2.5, elbow_n=0.3, elbow_f=0.3, hand_n="open", hand_f="open")
    E.sfx_at(t0 + 0.6, "land", 0.4, 0.0)
    Y.k(t0 + 0.7, face=-1, head_yaw=0.5)
    t = E.line("s4_05", t0 + 0.7, listeners=[])
    Y.k(t + 0.2, arm_n=0.12, arm_f=-0.12, elbow_n=0.35, elbow_f=0.35, hand_n="relax", hand_f="relax", face=1)
    # Самир прибегает с лупой
    E.jump(S, t - 1.0, visible=1.0, x=2500, y=1090, face=-1, crouch=0.0, lean=0.0, hold_n=props.magnifier(), hand_n="grip", arm_n=0.4, elbow_n=1.2)
    E.walk(S, t - 0.8, t + 0.8, 1700, e="out")
    E.cut(t + 0.2, 1620, 800, 1.35)
    S.k(t + 0.9, crouch=0.3, lean=0.35, arm_n=1.3, elbow_n=1.2, wide=0.9, brow_up=0.9, smile=0.9)
    t = E.line("s4_06", t + 1.0)
    # мама: «Машаллах. Видишь, как красиво, когда не торопишь?»
    E.jump(L, t - 0.8, visible=1.0, x=1180, y=1080, face=1, crouch=0.0, lean=0.0)
    E.walk(L, t - 0.8, t + 0.8, 1330, e="out")
    L.k(t + 0.9, crouch=0.35, lean=0.12, smile=0.8, squint=0.4, arm_n=0.4, elbow_n=1.0, arm_f=0.2, elbow_f=1.2)
    E.cut(t + 0.2, 1520, 700, 1.15)
    t = E.line("s4_07", t + 1.0)
    Y.k(t - 1.0, face=-1, smile=0.9, head_tilt=-0.1, blush=0.4)
    S.k(t - 0.5, crouch=0.0, lean=0.0, smile=0.8)
    E.dip(t + 1.0)
    return t + 1.0


def scene_5(E, t):
    """Ветер и дождик, вечер: «Возьми мою ленточку!» — подвязываем подсолнух вместе. Без вспышек и грома."""
    S, Y, L = E.S, E.Y, E.L
    E.meta["scene_starts"].append(t)
    E.loc(t, "yard", "windy", "windy")
    dx, dy = loc_yard.DOOR
    E.envk("stage", t - 0.1, 1.0, "linear"); E.envk("stage", t, 3.4, "linear")
    E.envk("wind", t, 0.6, "linear"); E.envk("wind", t + 3, 0.9)
    E.jump(Y, t, x=dx - 30, y=845, face=-1, crouch=0.0, lean=0.0, hold_n=None, smile=0.0, blush=0.0, brow_inner=0.7, wide=0.4, arm_n=0.12, elbow_n=0.35)
    E.jump(L, t, visible=1.0, x=dx + 100, y=835, face=-1, crouch=0.0, lean=0.0, smile=0.1, brow_inner=0.4, arm_n=0.12, elbow_n=0.35)
    E.jump(S, t, visible=1.0, x=dx + 220, y=830, face=-1, crouch=0.0, lean=0.0, hold_n=None, arm_n=0.12, elbow_n=0.35)
    Y.extra["wind"] = 1.0; L.extra["wind"] = 1.0; S.extra["wind"] = 0.8
    E.cut(t, 1800, 700, 1.0)
    E.walk(Y, t + 0.3, t + 2.2, 1480, y=1080)
    E.sfx_at(t + 0.2, "door_open", 0.5, 0.5)
    t = E.line("s5_01", t + 1.4, listeners=["leyla"])
    E.walk(L, t - 0.9, t + 1.2, 1720, y=1085)
    E.walk(S, t - 0.6, t + 1.3, 1900, y=1095)
    E.move(t - 1.0, t + 1.3, 1620, 760, 1.25)
    Y.k(t + 0.1, face=1)
    reach(Y, t + 0.2, "n", 0.55, -1.15, hand="grip")
    reach(Y, t + 0.2, "f", 0.45, -1.2, hand="grip")
    L.k(t + 1.3, face=-1)
    t = E.line("s5_02", t + 1.4)
    L.k(t - 1.2, arm_n=1.3, elbow_n=0.3, hand_n="point")
    S.k(t - 0.2, face=1)
    E.walk(S, t, t + 1.0, 2500, e="in")
    S.k(t + 1.05, visible=0.0)
    E.cut(t + 0.2, 1560, 720, 1.6)
    L.k(t + 0.4, arm_n=0.12, elbow_n=0.35, hand_n="relax", x=1650).k(t + 1.0, crouch=0.3, lean=0.15)
    reach(L, t + 0.6, "n", 0.95, -1.9, hand="grip")
    # Самир возвращается с палочкой
    t0 = t + 2.0
    E.jump(S, t0, visible=1.0, x=2400, face=-1, hold_n=props.stick(), hand_n="grip", arm_n=0.4, elbow_n=0.7)
    E.walk(S, t0, t0 + 1.2, 1800, e="out")
    E.cut(t0, 1720, 720, 1.35)
    S.k(t0 + 1.3, brow_inner=0.8, frown=0.3, arm_f=0.9, elbow_f=0.6, hand_f="open")
    t = E.line("s5_03", t0 + 1.3)
    E.envk("stick", t, 0.0); E.envk("stick", t + 0.5, 1.0)
    S.k(t + 0.4, hold_n=None, hand_n="relax", arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35)
    E.sfx_at(t + 0.4, "dig", 0.4, 0.2)
    # находчивость Ясмины: снимает бантик с косички
    t0 = t + 0.5
    E.cut(t0, 1470, 700, 2.2)
    Y.k(t0, arm_ik_n=0.0, arm_ik_f=0.0, arm_n=2.6, elbow_n=1.6, hand_n="pinch", wide=0.8, brow_up=0.9, smile=0.8, look_x=0.7, look_y=-0.3)
    Y.k(t0 + 0.6, arm_n=1.4, elbow_n=0.4, hold_n=props.ribbon_hand())
    t = E.line("s5_04", t0 + 0.5)
    E.cut(t + 0.2, 1640, 740, 1.4)
    Y.k(t + 0.2, hold_n=None)
    # мама завязывает бант — вставка
    E.insert(t + 0.4, t + 3.2, lambda c, tt, k: I.ribbon_stem(c, tt, k))
    E.envk("ribbon", t + 3.0, 0.0, "linear"); E.envk("ribbon", t + 3.2, 1.0, "linear")
    E.sfx_at(t + 1.0, "rope", 0.5, 0.0)
    t0 = t + 3.2
    E.cut(t0, 1560, 640, 1.6)
    L.k(t0, arm_ik_n=0.0, arm_n=0.5, elbow_n=1.6, crouch=0.3, smile=0.85, squint=0.5, look_x=0.5)
    Y.k(t0, arm_ik_n=0.0, arm_ik_f=0.0, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35, hand_n="relax", hand_f="relax", smile=0.9, blush=0.5)
    t = E.line("s5_05", t0 + 0.2)
    # Самир раскрывает зонтик над сестрой; начинается тихий дождик
    E.envk("rain", t, 0.0); E.envk("rain", t + 1.5, 1.0)
    E.walk(S, t, t + 0.9, 1380, y=1062)
    S.k(t + 0.9, face=1, hold_n=props.umbrella(1.0, (250, 200, 90)), hand_n="grip", arm_n=2.3, elbow_n=0.6)
    E.sfx_at(t + 0.7, "umbrella_open", 0.5, 0.2)
    E.cut(t + 0.4, 1520, 700, 1.35)
    E.cut(t + 1.4, 1480, 760, 2.2)
    Y.k(t + 1.4, face=1, look_x=0.6, look_y=-0.6, smile=0.5, brow_inner=0.3, head_tilt=0.1, blush=0.2)
    t = E.line("s5_06", t + 1.6)
    E.move(t, t + 3.0, 1560, 640, 1.2)
    E.dip(t + 3.0)
    E.envk("wind", t + 3.0, 0.4, "linear"); E.envk("wind", t + 3.1, 0.0, "linear")
    E.envk("rain", t + 3.0, 1.0, "linear"); E.envk("rain", t + 3.1, 0.0, "linear")
    return t + 3.0


def scene_6(E, t):
    """Через несколько недель, солнечный день: подсолнух выше всех. Благодарность. Печенье-дерево. Чай."""
    S, Y, L = E.S, E.Y, E.L
    E.meta["scene_starts"].append(t)
    E.loc(t, "yard", "day", "yard_morning")
    dx, dy = loc_yard.DOOR
    for A in (S, Y, L):
        A.extra["wind"] = 0.0
    E.envk("stage", t - 0.1, 3.4, "linear"); E.envk("stage", t, 6.0, "linear")
    E.envk("stick", t, 1.0, "linear"); E.envk("ribbon", t, 1.0, "linear"); E.envk("water", t, 0.0, "linear")
    E.jump(Y, t, x=dx - 40, y=845, face=-1, crouch=0.0, lean=0.0, hold_n=None, hand_n="relax", smile=0.6, brow_inner=0.0, wide=0.0, arm_n=0.12, elbow_n=0.35, blush=0.0)
    E.jump(S, t, x=dx + 60, y=840, face=-1, crouch=0.0, lean=0.0, hold_n=None, hand_n="relax", smile=0.6, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35)
    E.jump(L, t, visible=0.0, x=dx + 160, y=835, face=-1, crouch=0.0, lean=0.0, arm_n=0.12, elbow_n=0.35)
    E.cut(t, 2100, 640, 0.95)
    E.walk(Y, t + 0.3, t + 2.6, 1500, y=1090, e="out")
    E.walk(S, t + 0.5, t + 2.8, 1700, y=1095, e="out")
    E.sfx_at(t + 0.2, "door_open", 0.5, 0.5)
    # стоп — и взгляд вверх: медленная панорама снизу вверх на подсолнух (без слов)
    t0 = t + 2.9
    Y.k(t0, face=1, look_y=-0.9, head_pitch=-0.35, wide=1.0, brow_up=1.0, smile=0.6, open_mouth=0.4, mouth_shape="GASP")
    S.k(t0, face=-1, look_y=-0.9, head_pitch=-0.35, wide=0.8, brow_up=0.8, smile=0.6)
    E.cut(t0, 1590, 980, 1.6, auto=False)
    E.move(t0, t0 + 4.2, 1590, 420, 1.3, auto=False)
    E.sfx_at(t0 + 0.5, "sparkle", 0.3, 0.0)
    E.envk("sparkle", t0, 0.0); E.envk("sparkle", t0 + 2.5, 1.0); E.envk("sparkle", t0 + 5.0, 0.0)
    tl = E.line("r_yas_wow", t0 + 3.9, listeners=["samir"])
    Y.k(tl, open_mouth=0.0)
    # мама обнимает детей со спины: «Альхамдулиллях…»
    E.jump(L, tl - 0.5, visible=1.0, x=1600, y=1060, face=1)
    E.cut(tl + 0.2, 1600, 620, 1.2)
    L.k(tl + 0.2, arm_n=0.9, elbow_n=1.5, arm_f=0.8, elbow_f=1.6, hand_n="relax", hand_f="relax", smile=0.8, squint=0.5, look_y=-0.6, head_pitch=-0.2)
    Y.k(tl + 0.2, head_pitch=-0.2, look_y=-0.6)
    t = E.line("s6_01", tl + 0.6)
    # «Мама, а терпение — это тоже чудо?»
    E.cut(t + 0.2, 1520, 760, 2.2)
    Y.k(t + 0.2, face=1, head_pitch=0.0, head_yaw=0.6, look_x=0.6, look_y=-0.6, wide=0.2, brow_up=0.4, smile=0.4, head_tilt=0.12)
    t = E.line("s6_02", t + 0.35)
    E.cut(t + 0.2, 1620, 560, 2.1)
    L.k(t + 0.2, head_pitch=0.1, look_x=-0.5, look_y=0.5, smile=0.85, squint=0.6, head_tilt=-0.12)
    t = E.line("s6_03", t + 0.35)
    Y.k(t + 0.1, blush=0.6, smile=1.0, squint=0.6)
    # шутка: Самир «сажает» печенье
    t0 = t + 0.6
    E.jump(S, t0, x=1980, y=1100, face=1, crouch=0.42, lean=0.3, hold_n=props.cookie(), hand_n="grip", arm_n=1.1, elbow_n=0.6, look_y=0.6, head_pitch=0.2)
    E.jump(Y, t0, x=1500, face=1, head_yaw=0.45, crouch=0.0, head_pitch=0.0, look_y=0.0, blush=0.2)
    E.jump(L, t0, x=1380, face=1, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35, head_pitch=0.0)
    E.cut(t0, 1760, 760, 1.2)
    for i in range(3):
        tt = t0 + 0.2 + i * 0.3
        S.k(tt, elbow_n=0.6).k(tt + 0.15, elbow_n=0.9)
        E.sfx_at(tt + 0.1, "dig", 0.4, 0.4)
    Y.k(t0 + 0.6, look_x=0.6, brow_asym=0.6, brow_up=0.3)
    t = E.line("s6_04", t0 + 0.8)
    E.cut(t + 0.2, 1990, 800, 2.0)
    S.k(t + 0.2, crouch=0.2, lean=0.0, hold_n=None, hand_n="relax", head_pitch=0.0, look_y=0.0, face=-1, smile=0.6, brow_up=0.5, head_tilt=0.08, arm_n=0.12, elbow_n=0.35)
    t = E.line("s6_05", t + 0.35)
    S.k(t - 1.2, arm_f=0.6, elbow_f=2.0, hand_f="fist").k(t, arm_f=-0.12, elbow_f=0.35, hand_f="relax")
    # смех
    E.cut(t + 0.2, 1700, 700, 1.15)
    Y.k(t + 0.2, smile=1.0, squint=0.8, head_tilt=-0.12)
    t1 = E.line("s6_06", t + 0.3)
    Y.k(t1 - 1.0, lean=-0.08).k(t1, lean=0.0)
    tl = E.line("r_leyla_laugh", t1 + 0.1)
    L.k(t1, smile=1.0, squint=0.8)
    S.k(t1, smile=1.0, squint=0.7, blush=0.6)
    t = E.line("s6_07", tl + 0.2)
    L.k(t - 1.5, arm_n=1.3, elbow_n=0.4, hand_n="open").k(t + 0.2, arm_n=0.12, elbow_n=0.35, hand_n="relax")
    # все вместе идут в дом пить чай
    t0 = t + 0.3
    E.cut(t0, 2200, 620, 0.95)
    S.k(t0, crouch=0.0)
    E.walk(S, t0 + 0.2, t0 + 3.6, dx + 40, y=845)
    E.walk(Y, t0 + 0.4, t0 + 3.9, dx - 40, y=848)
    E.walk(L, t0 + 0.7, t0 + 4.3, dx - 120, y=840)
    E.sfx_at(t0 + 4.2, "door_open", 0.4, 0.6)
    for A in (S, Y, L):
        A.k(t0 + 4.6, visible=0.0)
    E.sfx_at(t0 + 4.8, "door_close", 0.4, 0.6)
    E.move(t0 + 3.0, t0 + 6.0, 1600, 520, 1.15)
    te = t0 + 6.3
    E.envk("endcard", te, 0.0, "linear"); E.envk("endcard", te + 0.8, 1.0)
    E.envk("fade", te + 5.2, 0.0, "linear"); E.envk("fade", te + 6.0, 1.0)
    return te + 6.0


def build(voice_dir):
    E = Episode(voice_dir)
    t = scene_1(E, 0.0)
    t = scene_2(E, t)
    t = scene_3(E, t)
    t = scene_4(E, t)
    t = scene_5(E, t)
    t = scene_6(E, t)
    E.meta["end"] = t
    E.n_frames = int(t * FPS) + 1
    E.prepare()
    return E


if __name__ == "__main__":
    E = build(sys.argv[1])
    print("длительность", round(E.meta["end"], 2), "с; сцены", [round(x, 1) for x in E.meta["scene_starts"]])
