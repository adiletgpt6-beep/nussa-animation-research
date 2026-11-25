"""Серия 1 «Семечко, которое не спешило» — постановка: камеры, фоны, действия героев, реквизит, эффекты, звук.

Время — в секундах серии. Каждый блок scene_N(E) добавляет ключи актёрам и событиям.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, d) for d in ("engine", "characters", "backgrounds")] + [HERE]
import numpy as np
import skia
from canvas import paint, W, H, gradient_rect, radial, col
from character import Character
from actor import Actor
from motion import Track, FPS, harden
import alsu, aidar, nuria, hedgehog, roof, props
from script import LINES

VOICE_DIR = os.environ.get("EP01_VOICE", "")
DUR = 283.0

FLOOR = dict(alsu=985, aidar=960, nuria=955)
POT = (1300, 1000)
BENCH_X = 1700


class Episode:
    def __init__(self, voice_dir=None):
        self.voice_dir = voice_dir or VOICE_DIR
        self.n_frames = int(DUR * FPS)
        self.alsu = Actor("alsu", Character(alsu.DESIGN), seed=1, extra=dict(step=58, run_step=100))
        self.aidar = Actor("aidar", Character(aidar.DESIGN), seed=2, extra=dict(step=66, run_step=112))
        self.nuria = Actor("nuria", Character(nuria.DESIGN), seed=3, extra=dict(step=52, run_step=80))
        self.actors = {"alsu": self.alsu, "aidar": self.aidar, "nuria": self.nuria}
        for name, a in self.actors.items():
            a.k(0, y=FLOOR[name], u={"alsu": 168, "aidar": 160, "nuria": 152}[name])
        # камера и мир
        self.cam = {k: Track(v) for k, v in dict(cx=1300.0, cy=700.0, zoom=0.82).items()}
        self.env = {k: Track(v) for k, v in dict(door=0.0, stage=0.0, wind=0.0, rain=0.0, flash=0.0, fade=0.0, water=0.0,
                                                  soil_hole=0.0, sparkle=0.0, pot_x=POT[0], tint=0.0, title=0.0, endcard=0.0, small_pot=0.0).items()}
        self.env["bg"] = Track("morning", step=True); self.env["bg2"] = Track("morning", step=True); self.env["bgmix"] = Track(0.0)
        self.hog = {k: Track(v, step=k in ("face", "vis")) for k, v in dict(x=1500.0, y=1000.0, face=-1, sniff=0.0, ball=0.0, vis=0.0, wet=0.0, sy=1.0).items()}
        self.pigeon = {k: Track(v, step=k in ("face", "vis")) for k, v in dict(x=-200.0, y=950.0, flap=0.0, peck=0.0, vis=0.0, face=1).items()}
        self.fx = []      # (t0, t1, kind, params)
        self.sfx = []     # (t, name, gain, pan)
        self.voice = []   # (t, line_id, who)
        self.meta = {}
        self.blanket = Track(0.0)
        self.bg_cache = {}
        self.lines_by_id = {l[0]: l for l in LINES}

    # ---------------------------------------------------------------- утилиты
    def line(self, lid, t):
        who = self.lines_by_id[lid][2]
        meta = json.load(open(os.path.join(self.voice_dir, lid + ".mp3.json")))
        self.actors[who].say(t, meta)
        self.voice.append((t, lid, who))
        al = meta["alignment"]
        return t + al["character_end_times_seconds"][-1]

    def cut(self, t, cx, cy, zoom):
        for k, v in (("cx", cx), ("cy", cy), ("zoom", zoom)):
            self.cam[k].key(t - 1e-3, self.cam[k](t - 1e-3), "linear")
            self.cam[k].key(t, v, "linear")

    def move_cam(self, t0, t1, cx, cy, zoom, e="inout"):
        for k, v in (("cx", cx), ("cy", cy), ("zoom", zoom)):
            self.cam[k].key(t0, self.cam[k](t0), "linear")
            self.cam[k].key(t1, v, e)

    def set_bg(self, t, preset, fade=0.0):
        if fade <= 0:
            self.env["bg"].key(t, preset, "linear"); self.env["bgmix"].key(t, 0.0, "linear")
        else:
            self.env["bg2"].key(t, preset, "linear")
            self.env["bgmix"].key(t, 0.0, "linear"); self.env["bgmix"].key(t + fade, 1.0, "inout")
            self.env["bg"].key(t + fade + 1e-3, preset, "linear"); self.env["bgmix"].key(t + fade + 2e-3, 0.0, "linear")

    def sfx_at(self, t, name, gain=1.0, pan=0.0):
        self.sfx.append((t, name, gain, pan))

    # ---------------------------------------------------------------- рисование
    def bg_image(self, preset):
        if preset not in self.bg_cache:
            self.bg_cache[preset] = roof.render_static(preset)
        return self.bg_cache[preset]

    def draw_frame(self, c, f):
        t = f / FPS
        cx, cy, z = self.cam["cx"](t), self.cam["cy"](t), self.cam["zoom"](t)
        z = max(z, 0.93)
        hw, hh = W / 2 / z, H / 2 / z
        cx = min(max(cx, hw), roof.WW - hw)
        cy = min(max(cy, hh), roof.WH - hh)
        bg, bg2, mixv = self.env["bg"](t), self.env["bg2"](t), self.env["bgmix"](t)
        P = roof.PRESETS[bg]
        shake = self.env["flash"](t) * 6
        c.save()
        c.translate(W / 2 + shake * math.sin(t * 90), H / 2)
        c.scale(z, z)
        c.translate(-cx, -cy)
        c.drawImage(self.bg_image(bg), 0, 0)
        if mixv > 0.001:
            p2 = skia.Paint(Alphaf=mixv)
            c.drawImage(self.bg_image(bg2), 0, 0, skia.SamplingOptions(), p2)
            P = roof.PRESETS[bg2] if mixv > 0.5 else P
        roof.draw_lights(c, P, t)
        roof.kiosk(c, 420, 880, P, self.env["door"](t))
        roof.bench(c, BENCH_X, 905, P)
        if self.env["small_pot"](t) > 0.5:
            roof.clay_pot(c, 830, 990, 0.75, P)
        wind = self.env["wind"](t)
        # объекты по глубине (y)
        items = []
        for name, a in self.actors.items():
            p = a.pose(f)
            if p["visible"] > 0.5:
                items.append((p["y"], "actor", (a, p)))
        items.append((POT[1] + 5, "pot", None))
        if self.hog["vis"](t) > 0.5:
            items.append((self.hog["y"](t), "hog", None))
        if self.pigeon["vis"](t) > 0.5:
            items.append((self.pigeon["y"](t), "pigeon", None))
        if self.blanket(t) > 0.01:
            items.append((960, "blanket", None))
        for _, kind, data in sorted(items, key=lambda q: q[0]):
            if kind == "actor":
                a, p = data
                a.ch.draw(c, p)
                if p.get("tears", 0) > 0.05:
                    J = a.ch.skeleton(p)
                    hx = p["x"] + J["head"][0] * p["u"] * p["face"]
                    hy = p["y"] + J["head"][1] * p["u"]
                    props.tears(c, hx + p["face"] * p["u"] * 0.12, hy + p["u"] * 0.05, t, p["tears"])
            elif kind == "pot":
                props.sunflower_pot(c, self.env["pot_x"](t), POT[1], self.env["stage"](t), P, roof.lit, wind=wind, t=t, scale=1.2,
                                    sparkle=self.env["sparkle"](t), soil_hole=self.env["soil_hole"](t), water=self.env["water"](t))
            elif kind == "hog":
                hg = self.hog
                st = (hg["x"](t) - hg["x"](max(0, t - 0.1))) * 0.6
                hedgehog.draw(c, hg["x"](t), hg["y"](t), 120, face=int(hg["face"](t)), sniff=math.sin(t * 9) * hg["sniff"](t),
                              ball=hg["ball"](t), step=hg["x"](t) * 0.08, wet=hg["wet"](t), sy=hg["sy"](t))
            elif kind == "pigeon":
                pg = self.pigeon
                props.pigeon(c, pg["x"](t), pg["y"](t), 70, face=int(pg["face"](t)), flap=abs(math.sin(t * 22)) * pg["flap"](t),
                             peck=max(0, math.sin(t * 8)) * pg["peck"](t))
            elif kind == "blanket":
                k = self.blanket(t)
                props.blanket_draw(c, BENCH_X + 60, 760 + (1 - k) * 60, 170, 120 * k)
        for (t0, t1, kind, prm) in self.fx:
            if t0 <= t <= t1:
                getattr(self, "fx_" + kind)(c, t, t0, t1, prm)
        c.restore()
        # экранные эффекты
        if self.env["rain"](t) > 0.01:
            props.rain(c, t, W, H, self.env["rain"](t), wind=0.4 + wind * 0.4)
        if wind > 0.3:
            props.leaves(c, t, W, H, n=int(10 * wind), wind=wind)
        self.grade(c, t, bg if mixv < 0.5 else bg2)
        fl = self.env["flash"](t)
        if fl > 0.01:
            c.drawRect(skia.Rect(0, 0, W, H), paint((235, 240, 255), 0.75 * fl))
        if self.env["title"](t) > 0.01:
            self.title_card(c, self.env["title"](t))
        if self.env["endcard"](t) > 0.01:
            self.end_card(c, self.env["endcard"](t))
        fd = self.env["fade"](t)
        if fd > 0.001:
            c.drawRect(skia.Rect(0, 0, W, H), paint((10, 8, 16), fd))

    def grade(self, c, t, preset):
        tint = {"morning": ((255, 220, 170), 0.06), "day": ((255, 255, 240), 0.03), "evening": ((255, 120, 90), 0.10),
                "storm": ((60, 80, 140), 0.22), "after_rain": ((220, 250, 255), 0.05)}[preset]
        p = skia.Paint(Color=col(tint[0], tint[1]))
        p.setBlendMode(skia.BlendMode.kMultiply if preset == "storm" else skia.BlendMode.kSoftLight)
        c.drawRect(skia.Rect(0, 0, W, H), p)
        # виньетка
        shader = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), W * 0.75, [col((0, 0, 0), 0.0), col((0, 0, 0), 0.0), col((20, 10, 30), 0.35)], [0.0, 0.6, 1.0])
        vp = skia.Paint(); vp.setShader(shader)
        c.drawRect(skia.Rect(0, 0, W, H), vp)

    def _font(self, size, bold=True):
        tf = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if bold else skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        return skia.Font(tf, size)

    def text(self, c, s, x, y, size, color, alpha=1.0, bold=True, outline=None):
        font = self._font(size, bold)
        w = font.measureText(s)
        if outline:
            p = paint(outline, alpha, style="stroke", width=size * 0.16)
            c.drawString(s, x - w / 2, y, font, p)
        c.drawString(s, x - w / 2, y, font, paint(color, alpha))

    def title_card(self, c, k):
        a = min(1.0, k)
        y = 440 + (1 - a) * 40
        self.text(c, "Сад на крыше", W / 2, y, 118, (255, 214, 80), a, outline=(120, 60, 40))
        self.text(c, "Семечко, которое не спешило", W / 2, y + 110, 58, (255, 255, 255), a, outline=(70, 50, 60))

    def end_card(self, c, k):
        c.drawRect(skia.Rect(0, 0, W, H), paint((255, 246, 226), min(1, k)))
        self.text(c, "Сад на крыше", W / 2, 470, 120, (240, 170, 40), min(1, k), outline=(120, 60, 40))
        self.text(c, "Терпение — это ждать и заботиться", W / 2, 590, 50, (90, 70, 80), min(1, k), bold=False)

    # ---- эффекты
    def fx_splash(self, c, t, t0, t1, prm):
        props.splash(c, prm["x"], prm["y"], t - t0, n=prm.get("n", 16), spread=prm.get("spread", 120), seed=prm.get("seed", 1))

    def fx_stream(self, c, t, t0, t1, prm):
        a = prm["actor"]
        p = a.pose(int(t * FPS))
        J = a.ch.skeleton(p)
        hx = p["x"] + J["wr_n"][0] * p["u"] * p["face"]
        hy = p["y"] + J["wr_n"][1] * p["u"]
        sx = hx + p["face"] * p["u"] * prm.get("dx", 0.95)
        sy = hy + p["u"] * prm.get("dy", -0.05)
        props.stream(c, sx, sy, prm["tx"], prm["ty"], t)

    def fx_lightning(self, c, t, t0, t1, prm):
        if t - t0 < 0.15:
            pts = [(prm["x"], 0)]
            rng = np.random.default_rng(int(t0 * 10))
            for k in range(7):
                pts.append((pts[-1][0] + rng.uniform(-60, 60), pts[-1][1] + 70))
            p = skia.Path(); p.moveTo(*pts[0])
            for q in pts[1:]:
                p.lineTo(*q)
            c.drawPath(p, paint((255, 255, 255), 0.9, style="stroke", width=5))

    def prepare(self):
        for d in (self.hog, self.pigeon, self.env):
            for name, tr in d.items():
                if name not in ("bg", "bg2", "bgmix", "fade", "title", "endcard", "flash"):
                    harden(tr)
        for a in self.actors.values():
            a.prepare(self.n_frames)


# ================================================================== постановка

def scene_1(E):
    A, B, N = E.alsu, E.aidar, E.nuria
    E.set_bg(0, "morning")
    # Айдар читает у горшка; Алсу вбегает с лейкой (хук: брызги через 1.6 с)
    B.k(0, x=1560, face=-1, head_yaw=0.35, head_pitch=0.25, look_y=0.5, arm_n=0.55, elbow_n=1.5, hold_n=props.book(), hand_n="grip",
        arm_f=0.4, elbow_f=1.4)
    A.k(0, x=240, face=1, hold_n=props.watering_can(1.0), hand_n="grip", arm_n=0.35, elbow_n=0.6, smile=0.8, look_x=0.4)
    A.k(1.35, x=1100, e="out")
    A.k(1.35, lean=0.0).k(1.5, lean=-0.18, e="out").k(1.75, lean=0.06).k(2.1, lean=0.0)   # торможение с откидыванием
    A.k(1.35, arm_n=0.35).k(1.55, arm_n=1.25, elbow_n=0.2, e="out").k(2.2, arm_n=0.5, elbow_n=0.6)  # лейка по инерции вперёд
    E.fx.append((1.55, 2.4, "splash", dict(x=1440, y=760, n=22, spread=140, seed=3)))
    E.sfx_at(0.0, "run_steps", 1.0, -0.4)
    E.sfx_at(1.55, "water_splash", 1.0, 0.3)
    E.cut(0, 900, 700, 1.0)
    E.move_cam(0.0, 1.5, 1300, 720, 0.95)
    # Айдар: испуг — прыжок со сжатием/растяжением
    B.k(1.6, sy=1.0, sx=1.0, jump=0).k(1.7, sy=0.88, sx=1.08, e="out").k(1.82, sy=1.12, sx=0.93, jump=40, e="out").k(2.0, sy=1.0, sx=1.0, jump=0, e="in").k(2.08, sy=0.94, sx=1.04).k(2.2, sy=1.0, sx=1.0)
    B.k(1.6, wide=0, brow_up=0, head_pitch=0.25, look_y=0.5).k(1.75, wide=1.0, brow_up=1.0, head_pitch=-0.05, look_y=0.0, look_x=0.4, smile=0.0, open_mouth=0.6, mouth_shape="GASP")
    B.k(2.1, open_mouth=0.0)
    B.k(1.8, arm_n=0.9, elbow_n=1.1).k(2.4, arm_n=0.55, elbow_n=1.5)
    E.sfx_at(1.75, "boing", 0.6, 0.3)
    t = E.line("s1_01", 2.2)
    B.k(2.2, brow_inner=-0.2, frown=0.3).k(4.0, head_tilt=-0.08)
    A.k(2.3, smile=0.3, brow_inner=0.5, squint=0.0, look_x=0.5, head_tilt=0.12)
    E.cut(2.2, 1330, 640, 1.35)
    t = E.line("s1_02", t + 0.25)
    A.k(t - 3.4, arm_n=0.35, elbow_n=0.6).k(t - 3.0, smile=0.9, squint=0.6, head_tilt=-0.1, brow_inner=0.3)
    A.k(t - 2.6, hip_x=-0.03).k(t - 1.6, hip_x=0.03).k(t - 0.6, hip_x=0.0)   # переминается
    t = E.line("s1_03", t + 0.2)
    B.k(t - 2.9, frown=0.0, brow_inner=0.0, smile=0.2, arm_f=0.6, elbow_f=2.3, hand_f="pinch")  # поправляет очки
    B.k(t - 2.2, arm_f=0.4, elbow_f=1.4, hand_f="relax", head_tilt=0.1, brow_asym=0.6)
    E.cut(t - 2.9, 1460, 600, 1.6)
    # дверь открывается: бабушка выходит
    td = t + 0.3
    E.env["door"].key(td, 0.0, "linear").key(td + 0.6, 1.0, "out")
    E.sfx_at(td, "door_open", 0.9, -0.6)
    N.k(0, x=540, visible=0.0, face=1).k(td + 0.25, visible=1.0, e="linear")
    N.k(td + 0.4, x=540).k(td + 3.2, x=800, e="inout")
    E.sfx_at(td + 0.6, "slow_steps", 0.8, -0.4)
    E.cut(td, 1000, 660, 0.95)
    for act, d in ((A, -1), (B, -1)):
        act.k(td + 0.3, head_yaw=0.35).k(td + 0.6, head_yaw=-0.3, look_x=-0.6)
    A.k(td + 0.6, face=1, head_yaw=-0.55).k(td + 1.1, face=-1, head_yaw=0.45, look_x=0.4)
    t = E.line("s1_04", td + 1.6)
    N.k(t - 2.0, arm_n=0.6, elbow_n=0.9, hand_n="pinch", hold_n=props.packet(), smile=0.6)
    A.k(td + 2.2, x=1100).k(td + 3.4, x=1060, e="inout")
    E.move_cam(td + 1.6, t, 940, 640, 1.2)
    t = E.line("s1_05", t + 0.3)
    A.k(t - 1.4, lean=0.15, head_tilt=-0.12, brow_up=0.6, look_x=0.4, look_y=0.2).k(t, lean=0.05)
    t = E.line("s1_06", t + 0.25)
    N.k(t - 6.2, smile=0.8, squint=0.5).k(t - 3.0, smile=0.7)
    # передача семечка: бабушка протягивает, Алсу берёт двумя руками
    A.k(t - 2.0, hold_n=None, hand_n="open", arm_n=0.9, elbow_n=0.7).k(t - 1.2, hold_n=props.packet(), hand_n="grip", arm_n=0.6, elbow_n=1.3)
    N.k(t - 1.2, hold_n=None, hand_n="relax", arm_n=0.1, elbow_n=0.3)
    E.cut(t - 6.4, 930, 600, 1.45)
    t = E.line("s1_07", t + 0.15)
    A.k(t - 1.7, crouch=0.12, sy=0.9, sx=1.06, e="out").k(t - 1.45, crouch=0.0, jump=70, sy=1.12, sx=0.92, wide=1, brow_up=1, smile=1.0, e="out")
    A.k(t - 1.15, jump=0, sy=1.0, sx=1.0, e="in").k(t - 1.05, sy=0.9, sx=1.06).k(t - 0.9, sy=1.0, sx=1.0, wide=0)
    E.sfx_at(t - 1.45, "jump_whoosh", 0.6, 0.0)
    E.sfx_at(t - 1.1, "land", 0.7, 0.0)
    # посадка: идёт к горшку, встаёт на колени, копает, кладёт семечко
    tp = t + 0.2
    A.k(tp, x=1060, face=-1).k(tp + 0.2, face=1).k(tp + 1.4, x=1185, e="inout")
    A.k(tp + 1.7, crouch=0.0).k(tp + 2.2, crouch=0.42, lean=0.35, e="out")
    A.k(tp + 2.2, hold_n=None, arm_ik_n=1.0, hx_n=0.75, hy_n=-0.55, hand_n="grip")
    for i in range(3):   # копает
        tt = tp + 2.4 + i * 0.4
        A.k(tt, hx_n=0.72, hy_n=-0.62).k(tt + 0.2, hx_n=0.80, hy_n=-0.45)
        E.sfx_at(tt + 0.15, "dig", 0.6, 0.1)
    E.env["soil_hole"].key(tp + 2.4, 0.0, "linear").key(tp + 3.4, 1.0)
    E.cut(tp + 1.7, 1250, 820, 1.7)
    t = E.line("s1_08", tp + 3.7)
    A.k(t - 1.0, hy_n=-0.5, hand_n="pinch", smile=0.4, squint=0.2).k(t - 0.4, hy_n=-0.40, hand_n="open")
    E.env["soil_hole"].key(t - 0.3, 1.0).key(t + 0.4, 0.0)
    E.sfx_at(t + 0.1, "pat_soil", 0.6, 0.1)
    A.k(t + 0.4, arm_ik_n=0.0, crouch=0.42).k(t + 0.9, lean=0.15, crouch=0.40)
    # пауза-ожидание: смотрит на горшок, ёжик выглядывает
    tw = t + 0.9
    E.cut(tw, 1250, 780, 2.0)
    A.k(tw, look_x=0.6, look_y=0.6, head_pitch=0.25, smile=0.2).k(tw + 1.5, head_tilt=0.12).k(tw + 2.8, head_tilt=-0.1, brow_up=0.4)
    E.hog["x"].key(0, 1520, "linear").key(tw + 0.5, 1520, "linear").key(tw + 1.6, 1395, "out")
    E.hog["vis"].key(0, 0.0, "linear").key(tw + 0.5, 1.0, "linear")
    E.hog["y"].key(0, 1010, "linear")
    E.hog["sniff"].key(tw + 1.6, 1.0).key(tw + 3.0, 0.3)
    E.sfx_at(tw + 1.7, "sniff", 0.6, 0.3)
    E.sfx_at(tw + 0.3, "clock_tick", 0.35, 0.0)
    t = E.line("s1_09", tw + 3.2)
    A.k(t - 1.6, look_x=0.0, look_y=0.0, head_pitch=0.0, head_yaw=0.0, brow_up=0.8, smile=0.0, arm_n=-0.6, elbow_n=1.2, hand_n="open")
    E.cut(t - 1.8, 1180, 640, 2.1)
    t = E.line("s1_10", t + 0.3)
    E.cut(t - 3.2, 1480, 600, 1.6)
    B.k(t - 3.2, head_pitch=0.0, look_y=0.0, smile=0.9, squint=0.6, head_tilt=0.1, hold_n=props.book(), arm_n=0.55, elbow_n=1.5)
    B.k(t - 2.0, head_tilt=-0.08).k(t - 1.0, head_tilt=0.06)
    t = E.line("s1_11", t + 0.3)
    A.k(t - 0.8, head_tilt=0.25, brow_up=0.9, brow_inner=0.4, smile=0.5, look_x=0.5)
    E.cut(t - 0.9, 1180, 650, 2.0)
    # реакция: бабушка смеётся, Айдар закрывает лицо книгой, ёжик чихает
    tr = t + 0.4
    E.cut(tr, 1150, 690, 1.0)
    N.k(tr, smile=1.0, squint=0.8, head_pitch=0.08).k(tr + 0.25, bob=0.03).k(tr + 0.5, bob=0.0).k(tr + 0.75, bob=0.03).k(tr + 1.0, bob=0.0)
    B.k(tr, arm_n=1.2, elbow_n=1.9).k(tr + 1.4, arm_n=0.55, elbow_n=1.5)
    E.line("r_laugh_nuria", tr + 0.05)
    E.hog["sy"].key(tr + 0.6, 1.0).key(tr + 0.75, 0.8).key(tr + 0.85, 1.15).key(tr + 1.0, 1.0)
    E.sfx_at(tr + 0.8, "sneeze_hog", 0.8, 0.3)
    # титр серии (≤ 4 с, после хука)
    tt = tr + 1.6
    E.env["title"].key(tt, 0.0, "linear").key(tt + 0.6, 1.0).key(tt + 3.2, 1.0).key(tt + 3.8, 0.0)
    E.move_cam(tt, tt + 3.8, 1300, 560, 0.85)
    E.meta["s1_end"] = tt + 3.8
    return tt + 3.8


def scene_2(E, t0):
    """Нетерпение: заглядывает, переливает воду, тащит горшок на солнце, засыпает на скамейке."""
    A, B, N = E.alsu, E.aidar, E.nuria
    # бабушка уходит в дверь, Айдар садится читать на скамейку
    N.k(t0, x=800, face=-1).k(t0 + 2.5, x=560, e="inout").k(t0 + 2.6, visible=0.0, e="linear")
    E.env["door"].key(t0 + 2.4, 1.0).key(t0 + 3.0, 0.0)
    E.sfx_at(t0 + 2.9, "door_close", 0.7, -0.6)
    B.k(t0, x=1560, face=-1).k(t0 + 1.5, x=1900, e="inout").k(t0 + 1.6, face=-1).k(t0 + 1.6, y=960).k(t0 + 2.2, y=935)
    B.k(t0 + 1.8, crouch=0.0).k(t0 + 2.3, crouch=0.48, lean=-0.05, e="out")
    B.k(t0 + 2.3, head_pitch=0.25, look_y=0.6, look_x=0.0)
    # Алсу на цыпочках к горшку, заглядывает
    A.k(t0, x=1185, face=1, crouch=0.40, lean=0.15).k(t0 + 0.6, crouch=0.0, lean=0.0)
    t = E.line("s2_01", t0 + 1.0)
    A.k(t - 2.6, x=1185).k(t - 0.6, x=1205).k(t - 0.6, lean=0.55, crouch=0.15, head_pitch=0.35, look_y=0.7, look_x=0.3, brow_up=0.5)
    A.k(t - 2.4, smile=0.6, squint=0.3, head_tilt=-0.1)
    E.cut(t0, 1300, 640, 1.2)
    E.cut(t - 1.4, 1240, 820, 2.0)
    A.k(t + 0.6, lean=0.0, crouch=0.0, head_pitch=0.0, look_y=0.0)
    # переливание: огромная лейка
    tw = t + 0.9
    A.k(tw, hold_n=props.watering_can(1.0, tilt=0.0), hand_n="grip", arm_n=0.4, elbow_n=0.6, x=1150)
    A.k(tw + 0.5, arm_n=1.25, elbow_n=0.4, lean=0.12, e="out").k(tw + 0.5, hold_n=props.watering_can(1.0, tilt=0.6))
    E.fx.append((tw + 0.6, tw + 3.6, "stream", dict(actor=A, tx=1300, ty=890, dx=1.15, dy=-0.3)))
    E.sfx_at(tw + 0.6, "pour", 1.0, 0.1)
    E.env["water"].key(tw + 0.6, 0.0).key(tw + 2.0, 1.0).key(tw + 3.4, 1.6)
    E.cut(tw, 1320, 700, 1.35)
    # ёжик рядом — его обливает
    E.hog["x"].key(tw, 1395, "linear").key(tw + 2.6, 1395, "linear")
    E.hog["wet"].key(tw + 2.6, 0.0).key(tw + 2.9, 1.0)
    E.fx.append((tw + 2.7, tw + 3.5, "splash", dict(x=1380, y=990, n=14, spread=90, seed=5)))
    E.hog["sy"].key(tw + 3.0, 1.0).key(tw + 3.15, 0.8).key(tw + 3.3, 1.15).key(tw + 3.45, 1.0)
    E.sfx_at(tw + 3.25, "sneeze_hog", 0.9, 0.3)
    E.hog["face"].key(tw + 3.6, -1, "linear").key(tw + 3.7, 1, "linear")
    E.hog["x"].key(tw + 3.8, 1395).key(tw + 6.5, 1950, "inout")
    E.sfx_at(tw + 3.9, "hog_huff", 0.7, 0.4)
    A.k(tw + 3.6, arm_n=0.4, elbow_n=0.6, lean=0.0, hold_n=props.watering_can(1.0, tilt=0.0), wide=0.8, brow_up=0.8, open_mouth=0.5, mouth_shape="GASP")
    A.k(tw + 4.2, open_mouth=0.0, wide=0.0)
    t = E.line("s2_02", tw + 3.9)
    B.k(t - 4.0, head_pitch=0.0, look_y=0.0, look_x=0.4, brow_inner=0.3, frown=0.2, arm_n=0.8, elbow_n=1.1)
    B.k(t - 2.0, head_tilt=0.1)
    E.cut(t - 4.1, 1700, 620, 1.55)
    t = E.line("s2_03", t + 0.3)
    A.k(t - 2.2, hold_n=None, frown=0.6, smile=0.0, brow_inner=0.6, arm_n=0.9, elbow_n=2.2, arm_f=0.9, elbow_f=2.2, head_tilt=-0.15, hand_n="fist")  # руки скрещены
    A.k(t - 1.0, hip_x=-0.04, head_tilt=-0.2)
    E.cut(t - 2.3, 1200, 640, 1.8)
    # тащит горшок на солнце
    tg = t + 0.5
    A.k(tg, frown=0.0, brow_inner=0.0, arm_n=0.5, elbow_n=0.8, arm_f=0.4, elbow_f=0.8, hand_n="relax")
    A.k(tg + 0.3, face=-1, x=1360).k(tg + 0.8, crouch=0.3, lean=-0.35, arm_ik_n=1.0, hx_n=-0.5, hy_n=-0.55, hand_n="grip")
    E.env["pot_x"].key(tg + 0.9, POT[0], "linear").key(tg + 4.0, 1060, "inout")
    A.k(tg + 0.9, x=1360).k(tg + 4.0, x=1120, e="inout")
    for k in range(4):
        E.sfx_at(tg + 1.0 + k * 0.7, "pot_scrape", 0.7, 0.0)
        A.k(tg + 1.0 + k * 0.7, sy=0.94, sx=1.04).k(tg + 1.35 + k * 0.7, sy=1.0, sx=1.0)
    A.k(tg + 1.2, squint=0.6, brow_inner=0.4, frown=0.3).k(tg + 4.0, squint=0.0, brow_inner=0.0, frown=0.0)
    E.cut(tg + 0.2, 1240, 700, 1.3)
    t = E.line("s2_04", tg + 4.4)
    A.k(t - 2.5, crouch=0.0, lean=0.0, arm_ik_n=0.0, face=1, x=1130, smile=1.0, squint=0.4)
    A.k(t - 2.0, arm_n=-2.6, elbow_n=0.3, hand_n="wave").k(t - 1.5, arm_n=-2.2, wrist_n=0.4).k(t - 1.0, arm_n=-2.7, wrist_n=-0.3).k(t - 0.5, arm_n=-2.3).k(t + 0.2, arm_n=0.12, elbow_n=0.35, hand_n="relax", wrist_n=0.0)
    E.cut(t - 2.6, 900, 560, 1.3)
    # время идёт: день -> вечер; сидит на скамейке, засыпает
    ts = t + 0.6
    E.set_bg(ts, "evening", fade=3.0)
    A.k(ts, x=1130, y=985).k(ts + 2.0, x=1765, y=950, e="inout")
    B.k(ts, crouch=0.48, y=935).k(ts + 0.6, crouch=0.0, y=960).k(ts + 0.8, face=1).k(ts + 2.4, x=2350, e="inout")
    A.k(ts + 2.2, face=-1).k(ts + 2.6, crouch=0.50, lean=-0.04, y=935)
    A.k(ts + 2.6, head_pitch=0.15, look_x=0.6, look_y=0.4, smile=0.3)
    E.move_cam(ts, ts + 3.0, 1500, 640, 1.15)
    A.k(ts + 4.5, lid=0.0).k(ts + 6.0, lid=0.5).k(ts + 6.5, lid=0.2).k(ts + 7.8, lid=0.7).k(ts + 8.6, lid=1.0)
    A.k(ts + 5.0, open_mouth=0.0).k(ts + 5.3, open_mouth=0.9, mouth_shape="GASP").k(ts + 6.1, open_mouth=0.0)   # зевок
    E.line("r_yawn_alsu", ts + 5.2)
    A.k(ts + 7.8, head_tilt=0.0).k(ts + 9.0, head_tilt=0.35, lean=0.08)
    A.k(ts + 9.0, breath=2.0)
    E.cut(ts + 4.0, 1640, 650, 1.7)
    # бабушка с пледом
    tb = ts + 9.2
    E.env["door"].key(tb, 0.0).key(tb + 0.5, 1.0)
    E.sfx_at(tb, "door_open", 0.6, -0.6)
    N.k(tb + 0.2, visible=1.0, x=540, face=1).k(tb + 3.6, x=1600, e="inout")
    E.sfx_at(tb + 0.6, "slow_steps", 0.7, -0.3)
    E.cut(tb + 0.4, 1100, 640, 1.0)
    E.blanket.key(tb + 4.2, 0.0, "linear").key(tb + 5.0, 1.0)
    N.k(tb + 3.8, lean=0.3, arm_n=1.1, elbow_n=0.6, arm_f=1.0, elbow_f=0.6).k(tb + 5.2, lean=0.08, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35)
    E.sfx_at(tb + 4.2, "cloth", 0.8, 0.2)
    E.cut(tb + 3.7, 1600, 640, 1.5)
    t = E.line("s2_05", tb + 5.4)
    N.k(t - 2.9, smile=0.8, squint=0.5, head_tilt=0.15, look_x=0.4, look_y=0.4)
    N.k(t - 1.5, arm_n=0.9, elbow_n=1.4).k(t - 0.5, arm_n=0.85, elbow_n=1.5).k(t + 0.5, arm_n=0.12, elbow_n=0.35)
    E.move_cam(t - 2.9, t + 2.0, 1640, 620, 1.9)
    # ночь -> утро (затемнение)
    E.env["fade"].key(t + 1.2, 0.0).key(t + 2.4, 1.0).key(t + 3.0, 1.0).key(t + 4.0, 0.0)
    E.sfx_at(t + 1.0, "crickets", 0.6, 0.0)
    return t + 3.0


def scene_3(E, t0):
    """Корешок: раскапывает, плачет, бабушка объясняет; сажают вместе."""
    A, B, N = E.alsu, E.aidar, E.nuria
    E.set_bg(t0, "morning")
    E.blanket.key(t0, 0.0, "linear")
    E.env["pot_x"].key(t0 - 1.5, 1060, "linear").key(t0 - 1.4, POT[0], "linear")
    N.k(t0, x=2150, visible=1.0, face=-1, lean=0.08, crouch=0.0)
    B.k(t0, x=300, face=1, visible=1.0, crouch=0.0, hold_n=None)
    A.k(t0, x=1765, y=935, face=-1, crouch=0.50, head_tilt=0.35, lid=1.0)
    A.k(t0 + 0.6, lid=0.0, head_tilt=0.0, arm_n=-2.8, elbow_n=0.4, arm_f=-2.6, elbow_f=0.4, sy=1.08, e="out")   # потягивается
    A.k(t0 + 1.4, arm_n=0.12, elbow_n=0.35, arm_f=-0.12, elbow_f=0.35, sy=1.0, crouch=0.0, y=985)
    E.line("r_stretch_alsu", t0 + 0.5)
    E.cut(t0, 1640, 640, 1.6)
    A.k(t0 + 1.6, x=1765).k(t0 + 3.0, x=1185, e="inout")
    E.cut(t0 + 1.6, 1300, 650, 1.1)
    A.k(t0 + 3.1, face=1).k(t0 + 3.4, lean=0.45, crouch=0.2, look_y=0.7, head_pitch=0.3)
    t = E.line("s3_01", t0 + 3.6)
    A.k(t - 2.6, brow_inner=0.7, frown=0.5, smile=0.0)
    E.cut(t - 2.8, 1100, 760, 1.9)
    # раскапывает
    tg = t + 0.2
    A.k(tg, crouch=0.42, lean=0.35, arm_ik_n=1.0, hx_n=0.75, hy_n=-0.55, hand_n="grip")
    for i in range(4):
        tt = tg + 0.3 + i * 0.35
        A.k(tt, hy_n=-0.62).k(tt + 0.17, hy_n=-0.45)
        E.sfx_at(tt + 0.12, "dig", 0.7, 0.0)
    E.env["soil_hole"].key(tg + 0.3, 0.0).key(tg + 1.4, 1.0)
    B.k(tg, x=300).k(tg + 1.8, x=880, e="inout")   # Айдар бежит
    t = E.line("s3_02", tg + 0.8)
    B.k(t - 1.8, brow_up=0.8, wide=0.7, arm_n=-1.3, elbow_n=0.4, hand_n="open").k(t + 1.2, brow_up=0.2, wide=0.0, arm_n=0.12, elbow_n=0.35, hand_n="relax")
    E.cut(t - 2.1, 1000, 640, 1.15)
    # семечко с корешком на ладони
    tr = t + 0.2
    A.k(tr, hx_n=0.5, hy_n=-1.15, hand_n="open", hold_n=props.seed(root=1.0), lean=0.1, head_pitch=0.35, look_y=0.6, look_x=0.4)
    E.cut(tr, 1120, 700, 2.4)
    t = E.line("s3_03", tr + 0.4)
    A.k(t - 5.0, wide=1.0, brow_up=0.9, open_mouth=0.6, mouth_shape="GASP").k(t - 4.2, open_mouth=0.0)
    A.k(t - 3.0, wide=0.0, brow_inner=1.0, brow_up=0.2, frown=0.9, tears=1.0, smile=0.0)
    A.k(t - 2.0, sy=0.97).k(t - 1.5, sy=1.0).k(t - 1.0, sy=0.97).k(t - 0.5, sy=1.0)   # всхлипы
        # бабушка подзывает со скамейки
    N.k(t, x=2150).k(t + 0.1, x=1905, y=955).k(t + 0.6, crouch=0.46, lean=-0.03, y=935)
    t = E.line("s3_04", t + 0.6)
    N.k(t - 2.2, arm_n=-0.6, elbow_n=1.2, hand_n="open", smile=0.6, brow_inner=0.4).k(t - 1.2, wrist_n=0.6).k(t - 0.6, wrist_n=-0.2).k(t, arm_n=0.12, elbow_n=0.35)
    E.cut(t - 2.6, 1650, 640, 1.5)
    # Алсу идёт к скамейке, садится рядом
    A.k(t, arm_ik_n=0.0, crouch=0.0, lean=0.0, hx_n=0.5, hy_n=-1.0).k(t + 0.1, arm_ik_n=1.0, hx_n=0.45, hy_n=-1.05)
    A.k(t + 0.3, x=1185).k(t + 2.6, x=1765, e="inout").k(t + 2.6, y=985).k(t + 2.9, y=935)
    A.k(t + 2.7, crouch=0.50, face=1, head_yaw=0.55)
    E.move_cam(t + 0.3, t + 2.8, 1800, 640, 1.35)
    B.k(t + 0.5, x=880).k(t + 3.2, x=1520, e="inout")
    t = E.line("s3_05", t + 3.2)
    N.k(t - 4.8, head_pitch=0.25, look_y=0.6, look_x=-0.3, smile=0.7, arm_n=0.4, elbow_n=1.2, hand_n="point")
    N.k(t - 1.0, head_pitch=0.0, look_y=0.0, look_x=0.4)
    A.k(t - 4.0, tears=0.4, frown=0.3)
    E.cut(t - 4.9, 1835, 610, 1.9)
    t = E.line("s3_06", t + 0.35)
    A.k(t - 2.0, tears=0.2, brow_inner=0.8, head_yaw=0.6, look_x=0.6, look_y=-0.2)
    E.cut(t - 2.1, 1770, 640, 2.3)
    t = E.line("s3_07", t + 0.4)
    N.k(t - 8.0, arm_n=0.7, elbow_n=0.9, hand_n="open").k(t - 6.0, arm_n=0.9, elbow_n=0.5, wrist_n=0.6)   # жест «вниз, в темноту»
    N.k(t - 4.0, arm_n=0.4, elbow_n=1.3, hand_n="point").k(t - 1.0, arm_n=0.12, elbow_n=0.35, hand_n="relax", smile=0.8)
    A.k(t - 6.0, tears=0.0, frown=0.0, brow_inner=0.2, look_y=0.5).k(t - 2.0, look_y=-0.2, brow_up=0.4)
    E.cut(t - 8.1, 1840, 610, 1.6)
    E.move_cam(t - 8.0, t, 1880, 600, 1.85)
    t = E.line("s3_08", t + 0.3)
    B.k(t - 1.7, smile=0.4, brow_up=0.5, arm_f=0.6, elbow_f=2.3, hand_f="pinch").k(t, arm_f=-0.12, elbow_f=0.35, hand_f="relax")
    E.cut(t - 1.8, 1560, 620, 1.7)
    t = E.line("s3_09", t + 0.35)
    N.k(t - 6.0, head_yaw=0.55, smile=0.6, squint=0.3, look_x=0.4).k(t - 3.0, arm_n=0.5, elbow_n=1.6, hand_n="open").k(t - 0.4, arm_n=0.12, elbow_n=0.35)
    E.cut(t - 6.1, 1890, 590, 2.3)
    t = E.line("s3_10", t + 0.4)
    A.k(t - 1.8, head_tilt=0.15, brow_inner=0.6, smile=0.0, look_x=0.5, look_y=-0.3)
    E.cut(t - 1.9, 1770, 640, 2.3)
    t = E.line("s3_11", t + 0.35)
    N.k(t - 6.1, smile=1.0, squint=0.7).k(t - 3.0, arm_n=1.3, elbow_n=1.0).k(t - 1.0, arm_n=1.2, elbow_n=1.2)   # обнимает
    A.k(t - 3.0, smile=0.9, squint=0.5, brow_inner=0.0, head_tilt=-0.2, lean=0.15)
    E.cut(t - 6.2, 1835, 610, 1.6)
    # сажают вместе
    tp = t + 0.6
    N.k(tp, arm_n=0.12, elbow_n=0.35, crouch=0.46).k(tp + 0.4, crouch=0.0, lean=0.08, y=955).k(tp + 0.6, face=-1).k(tp + 2.6, x=1240, e="inout")
    A.k(tp, lean=0.0).k(tp + 0.3, crouch=0.0, y=985).k(tp + 0.6, face=-1).k(tp + 2.4, x=1180, e="inout").k(tp + 2.5, face=1)
    B.k(tp + 0.4, face=-1).k(tp + 2.4, x=950, e="inout").k(tp + 2.5, face=1)
    A.k(tp + 2.6, crouch=0.42, lean=0.35, hx_n=0.4, hy_n=-0.55, hand_n="pinch")
    N.k(tp + 2.8, lean=0.45, crouch=0.12, arm_n=0.9, elbow_n=0.8, hand_n="open")
    E.move_cam(tp, tp + 2.8, 1120, 700, 1.4)
    E.env["soil_hole"].key(tp + 3.6, 1.0).key(tp + 4.6, 0.0)
    E.sfx_at(tp + 4.0, "pat_soil", 0.7, 0.0)
    t = E.line("s3_12", tp + 4.0)
    A.k(t - 2.0, hold_n=None, hand_n="open", hy_n=-0.45, smile=0.5, squint=0.3).k(t, arm_ik_n=0.0)
    E.cut(t - 2.3, 1110, 760, 2.1)
    return t + 1.2


def scene_4(E, t0):
    """Забота: расписание, голубь, ёжик, росток, рост по дням."""
    A, B, N = E.alsu, E.aidar, E.nuria
    E.set_bg(t0, "day")
    A.k(t0, crouch=0.0, lean=0.0, x=1180, face=1, arm_ik_n=0.0, hand_n="relax")
    N.k(t0, crouch=0.0, lean=0.08, x=1650, face=-1)
    B.k(t0, x=900, face=1, hold_n=props.chart(), arm_n=0.9, elbow_n=0.6, hand_n="grip")
    t = E.line("s4_01", t0 + 0.6)
    B.k(t - 5.4, smile=0.7, brow_up=0.6, head_tilt=0.08).k(t - 3.0, arm_n=1.1).k(t - 1.0, arm_f=0.6, elbow_f=2.3, hand_f="pinch").k(t, arm_f=-0.12, elbow_f=0.35, hand_f="relax")
    A.k(t - 4.0, face=-1, head_yaw=0.45, look_x=0.4, smile=0.4).k(t - 1.5, head_pitch=0.12).k(t - 1.1, head_pitch=-0.05).k(t - 0.7, head_pitch=0.12).k(t - 0.3, head_pitch=0.0)   # кивает
    E.cut(t0, 1050, 620, 1.35)
    # полив одной кружкой
    tc = t + 0.4
    B.k(tc, hold_n=None, arm_n=0.12, elbow_n=0.35)
    A.k(tc, face=1, hold_n=props.cup(), hand_n="grip").k(tc + 0.8, lean=0.3, arm_n=1.0, elbow_n=0.4).k(tc + 2.0, lean=0.0, arm_n=0.12, elbow_n=0.35)
    E.sfx_at(tc + 0.9, "pour_small", 0.8, 0.0)
    E.env["water"].key(tc + 0.9, 0.0, "linear").key(tc + 1.4, 0.6).key(tc + 2.4, 0.0)
    E.cut(tc, 1180, 760, 1.8)
    # дни идут: галочки в таблице (звук карандаша), голубь
    tp = tc + 2.6
    E.set_bg(tp, "morning", fade=1.0)
    E.pigeon["vis"].key(tp, 1.0, "linear")
    E.pigeon["x"].key(tp, 2700, "linear").key(tp + 1.4, 1360, "out")
    E.pigeon["y"].key(tp, 600, "linear").key(tp + 1.4, 1000, "out")
    E.pigeon["flap"].key(tp, 1.0, "linear").key(tp + 1.4, 0.0)
    E.pigeon["face"].key(tp, -1, "linear")
    E.pigeon["peck"].key(tp + 1.6, 1.0).key(tp + 3.0, 1.0)
    E.sfx_at(tp, "wings", 0.8, 0.5)
    E.sfx_at(tp + 1.4, "coo", 0.8, 0.2)
    E.cut(tp, 1300, 640, 1.2)
    t = E.line("s4_02", tp + 2.4)
    A.k(t - 2.0, face=1, x=1180, arm_n=-1.0, elbow_n=0.3, hand_n="open", brow_inner=-0.4, frown=0.2).k(t - 1.6, wrist_n=0.6).k(t - 1.2, wrist_n=-0.5).k(t - 0.6, wrist_n=0.5).k(t, arm_n=0.12, elbow_n=0.35, wrist_n=0.0, frown=0.0, brow_inner=0.0)
    E.pigeon["flap"].key(t - 0.6, 0.0).key(t - 0.4, 1.0)
    E.pigeon["x"].key(t - 0.5, 1360).key(t + 1.2, 2800, "in")
    E.pigeon["y"].key(t - 0.5, 1000).key(t + 1.2, 300, "in")
    E.sfx_at(t - 0.5, "wings", 1.0, 0.5)
    E.cut(t - 2.1, 1240, 680, 1.6)
    # ёжик нюхает горшок
    th = t + 0.8
    E.hog["vis"].key(th, 1.0, "linear")
    E.hog["wet"].key(th, 0.0, "linear")
    E.hog["face"].key(th, -1, "linear")
    E.hog["x"].key(th, 1900, "linear").key(th + 1.6, 1390, "inout")
    E.hog["sniff"].key(th + 1.6, 1.0)
    E.sfx_at(th + 1.7, "sniff", 0.7, 0.2)
    t = E.line("s4_03", th + 1.9)
    A.k(t - 3.0, lean=0.2, arm_n=0.9, elbow_n=0.4, hand_n="point", brow_inner=-0.2).k(t - 1.6, smile=0.9, squint=0.4, lean=0.05, arm_n=0.12, elbow_n=0.35, hand_n="relax")
    E.hog["ball"].key(t - 2.2, 0.0).key(t - 1.9, 1.0, "out")
    E.sfx_at(t - 2.0, "boing", 0.5, 0.2)
    E.hog["x"].key(t - 1.5, 1390).key(t + 0.8, 1900, "inout")
    E.hog["ball"].key(t + 0.8, 1.0).key(t + 1.2, 0.0)
    E.cut(t - 3.2, 1300, 740, 1.6)
    E.hog["vis"].key(t + 1.4, 0.0, "linear")
    # следующее утро — росток!
    ts = t + 1.6
    E.env["fade"].key(ts - 0.4, 0.0).key(ts, 1.0).key(ts + 0.4, 0.0)
    E.set_bg(ts, "morning")
    A.k(ts, x=600, face=1, hold_n=props.cup(), hand_n="grip").k(ts + 1.8, x=1160, e="inout")
    E.env["stage"].key(ts, 0.0, "linear").key(ts + 0.1, 1.0, "linear")
    E.cut(ts, 1000, 640, 1.1)
    A.k(ts + 1.9, wide=1.0, brow_up=1.0, open_mouth=0.7, mouth_shape="GASP", lean=0.2).k(ts + 2.5, open_mouth=0.0)
    E.sfx_at(ts + 1.9, "sparkle", 0.6, 0.0)
    E.cut(ts + 1.9, 1220, 820, 2.3)
    t = E.line("s4_04", ts + 2.6)
    A.k(t - 2.0, wide=0.3, smile=1.0, squint=0.3, jump=40, sy=1.08, e="out").k(t - 1.6, jump=0, sy=1.0, e="in").k(t - 1.2, jump=30, e="out").k(t - 0.9, jump=0, e="in")
    E.sfx_at(t - 1.6, "land", 0.6, 0.0); E.sfx_at(t - 0.9, "land", 0.5, 0.0)
    E.cut(t - 2.1, 1150, 640, 1.4)
    B.k(t - 1.0, x=900).k(t + 0.8, x=1000, e="inout")
    N.k(t - 1.0, x=1650).k(t + 1.6, x=1420, e="inout")
    t = E.line("s4_05", t + 0.6)
    B.k(t - 2.4, crouch=0.3, lean=0.4, wide=0.8, brow_up=0.9, smile=0.8, arm_f=0.6, elbow_f=2.3, hand_f="pinch").k(t, arm_f=-0.12, elbow_f=0.35, hand_f="relax")
    E.cut(t - 2.5, 1150, 700, 1.6)
    t = E.line("s4_06", t + 0.3)
    N.k(t - 3.3, smile=0.9, squint=0.5, head_tilt=0.12, arm_n=0.6, elbow_n=1.3, hand_n="open")
    A.k(t - 3.0, face=-1, head_yaw=0.5, look_x=0.5, look_y=-0.3, smile=0.8)
    E.cut(t - 3.4, 1350, 610, 1.55)
    # таймлапс роста: дни, свет меняется, Алсу меряется ростом
    tl = t + 0.6
    N.k(tl, arm_n=0.12, elbow_n=0.35)
    presets = ["day", "evening", "morning", "day", "morning"]
    for i, pr in enumerate(presets):
        E.set_bg(tl + i * 1.6, pr, fade=0.8)
        E.sfx_at(tl + i * 1.6, "time_whoosh", 0.4, 0.0)
    E.env["stage"].key(tl, 1.0).key(tl + 8.0, 4.0, "inout")
    E.move_cam(tl, tl + 8.0, 1240, 660, 1.2)
    B.k(tl, x=1000).k(tl + 0.4, face=-1).k(tl + 2.0, x=820)
    A.k(tl + 5.5, face=1, x=1160).k(tl + 6.5, x=1225).k(tl + 6.6, face=-1)
    A.k(tl + 7.0, arm_n=-2.5, elbow_n=1.2, hand_n="open").k(tl + 7.8, smile=1.0, squint=0.5, wide=0.4)
    A.k(tl + 9.0, arm_n=0.12, elbow_n=0.35, hand_n="relax")
    E.line("r_giggle_alsu", tl + 7.8)
    return tl + 9.4


def scene_5(E, t0):
    """Буря: ветер, бегут, подвязывают, бабушка с зонтом."""
    A, B, N = E.alsu, E.aidar, E.nuria
    E.set_bg(t0, "evening")
    E.set_bg(t0 + 0.5, "storm", fade=2.5)
    E.env["wind"].key(t0, 0.0).key(t0 + 3.0, 1.0)
    A.k(t0, visible=0.0, x=500); B.k(t0, visible=0.0, x=500); N.k(t0, visible=0.0, x=500)
    E.sfx_at(t0, "wind_rise", 1.0, 0.0)
    E.cut(t0, 1240, 640, 1.2)
    E.env["stage"].key(t0, 4.0, "linear")
    E.env["door"].key(t0 + 3.0, 0.0).key(t0 + 3.3, 1.0, "out")
    E.sfx_at(t0 + 3.0, "door_bang", 1.0, -0.6)
    B.k(t0 + 3.2, visible=1.0, x=540, face=1, wide=0.8, brow_up=0.6, brow_inner=0.6).k(t0 + 4.6, x=1000, e="inout")
    A.k(t0 + 3.5, visible=1.0, x=540, face=1).k(t0 + 5.6, x=1160, e="inout")
    E.sfx_at(t0 + 3.2, "run_steps", 1.0, -0.3)
    E.cut(t0 + 3.1, 900, 640, 1.0)
    t = E.line("s5_01", t0 + 3.7)
    E.fx.append((t - 1.0, t - 0.8, "lightning", dict(x=1800)))
    E.env["flash"].key(t - 1.0, 0.0, "linear").key(t - 0.95, 1.0, "linear").key(t - 0.6, 0.0)
    E.sfx_at(t - 0.5, "thunder", 1.0, 0.0)
    E.env["rain"].key(t - 1.0, 0.0).key(t + 1.5, 1.0)
    E.sfx_at(t - 1.0, "rain", 1.0, 0.0)
    # держит стебель, Айдар подвязывает к палке
    th = t + 0.2
    A.k(th, crouch=0.15, lean=0.15, arm_ik_n=1.0, hx_n=0.55, hy_n=-1.5, hand_n="grip", arm_f=0.9, elbow_f=0.6, brow_inner=-0.4, frown=0.3)
    B.k(th, x=1000).k(th + 1.0, x=1400, e="inout").k(th + 1.1, face=-1).k(th + 1.3, crouch=0.35, lean=0.3, hold_n=props.stick(), hand_n="grip", arm_n=1.0, elbow_n=0.6)
    E.cut(th, 1300, 700, 1.4)
    N.k(th + 0.8, visible=1.0, x=540, face=1).k(th + 3.4, x=1060, e="inout").k(th + 3.4, hold_n=props.umbrella(1.0), arm_n=-1.9, elbow_n=0.9, hand_n="grip")
    E.sfx_at(th + 3.0, "umbrella_open", 0.8, -0.2)
    t = E.line("s5_02", th + 3.6)
    N.k(t - 3.5, brow_inner=0.4, smile=0.3)
    E.cut(t - 3.7, 1230, 620, 1.25)
    for i in range(3):   # вяжет узел
        tt = t - 2.5 + i * 0.6
        B.k(tt, arm_n=1.2, elbow_n=0.5).k(tt + 0.3, arm_n=0.9, elbow_n=0.9)
        E.sfx_at(tt + 0.2, "rope", 0.6, 0.2)
    E.fx.append((t + 0.2, t + 0.4, "lightning", dict(x=600)))
    E.env["flash"].key(t + 0.2, 0.0, "linear").key(t + 0.25, 0.8, "linear").key(t + 0.6, 0.0)
    E.sfx_at(t + 0.7, "thunder", 0.8, -0.3)
    t = E.line("s5_03", t + 0.9)
    A.k(t - 2.3, brow_inner=0.3, frown=0.0, smile=0.4, look_y=-0.4, head_pitch=-0.15)
    E.cut(t - 2.4, 1180, 640, 2.0)
    # обнимаются под зонтом, затемнение
    tt = t + 0.6
    B.k(tt, crouch=0.0, lean=0.0, hold_n=None, face=1, x=1330, arm_n=0.12, elbow_n=0.35)
    A.k(tt, arm_ik_n=0.0, crouch=0.0, lean=0.05, smile=0.7, squint=0.3, brow_inner=0.0)
    E.move_cam(tt, tt + 4.0, 1220, 600, 1.05)
    E.env["wind"].key(tt + 1.0, 1.0).key(tt + 4.5, 0.3)
    E.env["fade"].key(tt + 3.0, 0.0).key(tt + 4.6, 1.0)
    E.env["rain"].key(tt + 4.0, 1.0).key(tt + 4.6, 0.0)
    return tt + 4.6


def scene_6(E, t0):
    """Утро после дождя: подсолнух расцвёл; финальная шутка."""
    A, B, N = E.alsu, E.aidar, E.nuria
    E.set_bg(t0, "after_rain")
    E.env["wind"].key(t0, 0.0, "linear")
    E.env["fade"].key(t0, 1.0, "linear").key(t0 + 1.2, 0.0)
    E.env["stage"].key(t0, 6.0, "linear")
    E.env["sparkle"].key(t0, 1.0, "linear")
    N.k(t0, visible=0.0, hold_n=None, arm_n=0.12, elbow_n=0.35, x=540)
    B.k(t0, visible=0.0, x=540)
    A.k(t0, visible=0.0, x=540)
    E.sfx_at(t0, "birds_morning", 1.0, 0.0)
    E.cut(t0, 1260, 560, 1.0)
    E.move_cam(t0, t0 + 3.0, 1250, 600, 1.1)
    E.env["door"].key(t0 + 1.6, 0.0).key(t0 + 2.0, 1.0)
    E.sfx_at(t0 + 1.6, "door_open", 0.7, -0.6)
    A.k(t0 + 1.8, visible=1.0, x=540, face=1, smile=0.3).k(t0 + 3.4, x=820, e="out")
    A.k(t0 + 3.4, wide=1.0, brow_up=1.0, open_mouth=0.8, mouth_shape="GASP", lean=-0.12, sy=1.06).k(t0 + 4.0, sy=1.0)
    E.sfx_at(t0 + 3.4, "sparkle", 0.8, 0.0)
    A.k(t0 + 4.2, open_mouth=0.0).k(t0 + 4.4, x=820).k(t0 + 5.6, x=1120, e="inout")
    E.cut(t0 + 3.4, 900, 600, 1.6)
    E.cut(t0 + 4.4, 1250, 560, 1.05)
    t = E.line("s6_01", t0 + 6.0)
    A.k(t - 1.9, wide=0.6, brow_up=0.6, head_pitch=-0.35, look_y=-0.8, look_x=0.4, smile=0.6, lean=-0.08, head_yaw=0.3)
    E.cut(t - 2.0, 1180, 520, 1.6)
    N.k(t - 1.0, visible=1.0, x=540, face=1).k(t + 2.0, x=1480, e="inout")
    B.k(t - 0.6, visible=1.0, x=540, face=1).k(t + 1.6, x=940, e="inout")
    t = E.line("s6_02", t + 2.4)
    N.k(t - 5.0, face=-1).k(t - 4.8, smile=0.9, squint=0.6, head_pitch=-0.2, look_y=-0.5, arm_n=-0.5, elbow_n=1.0, hand_n="open")
    N.k(t - 2.0, head_pitch=0.0, look_y=0.0, arm_n=0.12, elbow_n=0.35)
    E.cut(t - 5.3, 1330, 560, 1.4)
    t = E.line("s6_03", t + 0.4)
    A.k(t - 2.0, face=1, head_yaw=0.5, look_x=0.5, look_y=-0.3, head_tilt=0.15, smile=0.4, brow_up=0.5)
    E.cut(t - 2.1, 1200, 600, 2.0)
    t = E.line("s6_04", t + 0.35)
    N.k(t - 3.1, smile=1.0, squint=0.8).k(t - 2.5, bob=0.025).k(t - 2.2, bob=0.0).k(t - 1.9, bob=0.025).k(t - 1.6, bob=0.0)
    E.cut(t - 3.2, 1460, 580, 1.9)
    # финальная шутка: Айдар сажает печенье
    tj = t + 0.4
    E.env["small_pot"].key(t0, 1.0, "linear")
    B.k(tj, face=-1).k(tj + 1.2, x=720, e="inout").k(tj + 1.25, face=1).k(tj + 1.3, crouch=0.42, lean=0.35, hold_n=props.cookie(), hand_n="pinch", arm_n=1.1, elbow_n=0.5)
    E.cut(tj, 1000, 640, 1.2)
    t = E.line("s6_05", tj + 1.6)
    A.k(t - 1.5, face=-1, head_yaw=0.5, brow_up=0.7, head_tilt=-0.12, look_x=0.4, look_y=0.3)
    t = E.line("s6_06", t + 0.3)
    B.k(t - 4.3, head_yaw=0.0, look_x=0.0, smile=0.6, brow_up=0.6).k(t - 2.0, arm_f=0.6, elbow_f=2.3, hand_f="pinch", smile=1.0).k(t, arm_f=-0.12, elbow_f=0.35, hand_f="relax")
    B.k(t - 2.6, hold_n=None, hand_n="open")
    E.cut(t - 4.4, 820, 660, 1.9)
    t = E.line("s6_07", t + 0.3)
    A.k(t - 2.4, smile=1.0, squint=0.8, bob=0.02).k(t - 2.1, bob=0.0).k(t - 1.8, bob=0.02).k(t - 1.5, bob=0.0)
    N.k(t - 2.4, smile=1.0, squint=0.8)
    E.cut(t - 2.5, 1050, 620, 1.15)
    # ёжик под подсолнухом: падает семечко, чихает
    th = t + 0.4
    E.hog["vis"].key(th, 1.0, "linear"); E.hog["ball"].key(th, 0.0, "linear"); E.hog["wet"].key(th, 0.0, "linear")
    E.hog["x"].key(th, 1420, "linear"); E.hog["face"].key(th, -1, "linear"); E.hog["y"].key(th, 1010, "linear")
    E.cut(th, 1350, 860, 2.2)
    E.hog["sy"].key(th + 1.2, 1.0).key(th + 1.3, 0.85).key(th + 1.45, 1.15).key(th + 1.6, 1.0)
    E.sfx_at(th + 0.9, "seed_drop", 0.8, 0.1)
    E.sfx_at(th + 1.35, "sneeze_hog", 1.0, 0.1)
    E.line("r_laugh_aidar", th + 1.6)
    te = th + 2.6
    E.env["endcard"].key(te, 0.0).key(te + 0.8, 1.0).key(te + 4.4, 1.0)
    E.env["fade"].key(te + 4.4, 0.0).key(te + 5.0, 1.0)
    return te + 5.0


def build(voice_dir=None):
    E = Episode(voice_dir)
    starts = [0.0]
    t = scene_1(E); starts.append(t)
    t = scene_2(E, t); starts.append(t)
    t = scene_3(E, t); starts.append(t)
    t = scene_4(E, t); starts.append(t)
    t = scene_5(E, t); starts.append(t)
    t = scene_6(E, t)
    E.meta["scene_starts"] = starts
    E.meta["end"] = t
    E.n_frames = int(math.ceil(t * FPS))
    E.prepare()
    return E
