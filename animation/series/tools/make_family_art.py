"""Библиотека семьи: листы героев (повороты, вид со спины, эмоции, формы рта), групповой портрет,
фоны локаций и обложка YouTube 1280×720. python tools/make_family_art.py OUT_DIR"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, d) for d in ("engine", "characters", "backgrounds")]
import skia, numpy as np
from canvas import paint, col
from character import Character
from face import mouth_vec, MOUTH
import samir, yasmina, leyla, hedgehog, props, loc_yard, loc_home
from home_common import LIGHT

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def text(c, s, x, y, size, color, outline=None, ow=0.16, center=True, bold=True):
    f = skia.Font(skia.Typeface.MakeFromFile(FB if bold else FR), size)
    w = f.measureText(s)
    xx = x - w / 2 if center else x
    if outline:
        c.drawString(s, xx, y, f, paint(outline, style="stroke", width=size * ow))
    c.drawString(s, xx, y, f, paint(color))


EMO = {
    "радость": dict(mouth=mouth_vec({"SMILE_OPEN": 1}), squint=0.6, brow_up=0.3),
    "удивление": dict(mouth=mouth_vec({"GASP": 1}), wide=1.0, brow_up=1.0),
    "грусть": dict(mouth=mouth_vec({"X": 1}) - np.array([0, 0, 0, 0.5, 0, 0, 0]), brow_inner=1.0, look=(0.0, 0.4)),
    "слёзы": dict(mouth=mouth_vec({"CRY": 1}), brow_inner=1.0, squint=0.3),
    "задумчивость": dict(mouth=mouth_vec({"X": 1}), look=(0.5, -0.6), brow_asym=0.7),
    "недовольство": dict(mouth=mouth_vec({"X": 1}) - np.array([0, 0, 0, 0.35, 0, 0, 0]), brow_inner=-0.5),
    "смех": dict(mouth=mouth_vec({"SMILE_OPEN": 1, "A": 0.6}), squint=0.9, brow_up=0.5),
    "нежность": dict(mouth=mouth_vec({"X": 1}) + np.array([0, 0, 0, 0.35, 0, 0, 0]), squint=0.4, blush=0.8),
}


def sheet(mod, name, desc, u):
    ch = Character(mod.DESIGN)
    s = skia.Surface(2400, 1500); c = s.getCanvas(); c.clear(col((248, 244, 236)))
    text(c, name, 1200, 80, 64, (80, 60, 70))
    text(c, desc, 1200, 130, 28, (120, 100, 110), bold=False)
    base = dict(face_st=dict(mouth=mouth_vec({"X": 0.6, "SMILE_OPEN": 0.4}), squint=0.2))
    for i, (yaw, face, back) in enumerate(((0.0, 1, 0), (0.45, 1, 0), (0.9, 1, 0), (0.45, -1, 0), (0.0, 1, 1))):
        p = dict(base, x=260 + i * 300, y=760, u=u, face=face, head_yaw=yaw, back=back)
        ch.draw(c, p)
    text(c, "анфас · 3/4 · профиль · 3/4 влево · со спины", 860, 820, 26, (120, 100, 110), bold=False)
    # эмоции (крупно головы)
    for i, (en, st) in enumerate(EMO.items()):
        x, y = 1730 + (i % 4) * 170, 300 + (i // 4) * 300
        p = dict(x=x, y=y + 560, u=150, face=1, head_yaw=0.25, face_st=dict(st))
        c.save(); c.clipRect(skia.Rect(x - 80, y - 110, x + 80, y + 140))
        J = ch.skeleton(p); p["y"] = y - J["head"][1] * 150
        ch.draw(c, p)
        c.restore()
        text(c, en, x, y + 175, 19, (100, 80, 90), bold=False)
    # формы рта для фонем
    for i, v in enumerate(("X", "MBP", "A", "O", "U", "I", "E", "Y", "FV", "S", "SH", "T", "K", "R")):
        x, y = 140 + i * 160, 1160
        p = dict(x=x, y=0, u=140, face=1, head_yaw=0.0, face_st=dict(mouth=mouth_vec({v: 1})))
        J = ch.skeleton(p); p["y"] = y - J["head"][1] * 140
        c.save(); c.clipRect(skia.Rect(x - 75, y - 90, x + 75, y + 90))
        ch.draw(c, p)
        c.restore()
        text(c, v, x, y + 130, 22, (100, 80, 90))
    text(c, "формы рта (виземы) — М/Б/П сомкнуты, А/О/У/И/Э различимы", 1200, 1440, 26, (120, 100, 110), bold=False)
    s.makeImageSnapshot().save(os.path.join(OUT, f"sheet_{mod.DESIGN.name}.png"))


sheet(samir, "Самир, 9 лет — старший брат", "добрый, заботливый, любознательный, немного озорной; лупа и блокнот", 130)
sheet(yasmina, "Ясмина (Ясми), 5–6 лет — младшая сестра", "весёлая, искренняя, эмоциональная, любит вопросы; находчивая", 140)
sheet(leyla, "Мама Лейла", "спокойная, тёплая, мудрая; объясняет делом и вопросом, без нотаций", 110)

# ---------- групповой портрет семьи
s = skia.Surface(1920, 1080); c = s.getCanvas()
L = loc_yard.render_layers("day")
c.save(); c.translate(-760, -150)
for k in ("far", "mid", "main"):
    c.drawImage(L[k], 0, 0)
c.restore()
sm = lambda **kw: dict(mouth=mouth_vec({"SMILE_OPEN": 0.7, "X": 0.3}), squint=0.45, **kw)
Character(leyla.DESIGN).draw(c, dict(x=980, y=1060, u=150, face=1, head_yaw=0.25, arm_n=0.5, elbow_n=1.4, face_st=sm(look=(0.2, 0.1))))
Character(samir.DESIGN).draw(c, dict(x=1270, y=1080, u=165, face=-1, head_yaw=0.3, hold_n=props.magnifier(), hand_n="grip", arm_n=0.9, elbow_n=1.2, face_st=sm(brow_up=0.4)))
Character(yasmina.DESIGN).draw(c, dict(x=720, y=1085, u=175, face=1, head_yaw=0.3, arm_n=-2.5, elbow_n=0.3, hand_n="wave", face_st=sm(wide=0.4, brow_up=0.6)))
s.makeImageSnapshot().save(os.path.join(OUT, "family_lineup.png"))

# ---------- обложка YouTube
s = skia.Surface(1920, 1080); c = s.getCanvas()
c.save(); c.translate(-880, -120); c.scale(1.0, 1.0)
for k in ("far", "mid", "main"):
    c.drawImage(L[k], 0, 0)
lit = lambda col_, P_, kk=1.0: col_
props.sunflower_pot(c, 2380, 1130, 6.0, LIGHT["day"], lit, t=0.3, scale=2.1, sparkle=1.0, pot=False, stick=1.0, ribbon=1.0)
c.restore()
Character(leyla.DESIGN).draw(c, dict(x=1140, y=1110, u=150, face=1, head_yaw=0.3, face_st=dict(mouth=mouth_vec({"SMILE_OPEN": 0.6, "X": 0.4}), squint=0.5, look=(0.4, -0.3))))
Character(samir.DESIGN).draw(c, dict(x=1720, y=1200, u=230, face=-1, head_yaw=0.35, hold_n=props.magnifier(1.2), hand_n="grip", arm_n=1.0, elbow_n=1.3,
                                     face_st=dict(mouth=mouth_vec({"SMILE_OPEN": 1}), brow_up=0.7, wide=0.4, look=(0.3, -0.5))))
Character(yasmina.DESIGN).draw(c, dict(x=560, y=1250, u=330, face=1, head_yaw=0.3, arm_n=-2.6, elbow_n=0.4, hand_n="open",
                                       face_st=dict(mouth=mouth_vec({"SMILE_OPEN": 1}), wide=0.7, brow_up=0.8, look=(0.6, -0.5))))
hedgehog.draw(c, 1330, 1070, 150, face=-1, sniff=0.3)
grad = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 380)], [col((255, 255, 255), 0.6), col((255, 255, 255), 0.0)], [0, 1])
gp = skia.Paint(); gp.setShader(grad); c.drawRect(skia.Rect(0, 0, 1920, 380), gp)
text(c, "Семечко,", 560, 160, 150, (255, 210, 60), (110, 60, 40))
text(c, "которое не спешило", 760, 290, 100, (255, 255, 255), (90, 60, 70))
s.makeImageSnapshot().resize(1280, 720).save(os.path.join(OUT, "thumbnail_1280x720.png"))

# ---------- превью локаций
s = skia.Surface(2400, 1400); c = s.getCanvas(); c.clear(col((248, 244, 236)))
shots = [("Двор и сад — утро", "yard", "morning"), ("Двор — закат", "yard", "golden"), ("Двор — ветер", "yard", "windy"),
         ("Прихожая", "hallway", "morning"), ("Кухня", "kitchen", "morning"), ("Детская — вечер", "kidsroom", "golden")]
for i, (title, loc, pr) in enumerate(shots):
    Ls = loc_yard.render_layers(pr) if loc == "yard" else loc_home.render_layers(loc, pr)
    x, y = 40 + (i % 3) * 790, 60 + (i // 3) * 680
    c.save(); c.translate(x, y); c.clipRect(skia.Rect(0, 0, 760, 560))
    sc = 760 / (3400 if loc == "yard" else 2600)
    c.scale(sc, sc)
    for k in ("far", "mid", "main", "fg"):
        if Ls.get(k) is not None:
            c.drawImage(Ls[k], 0, 0)
    c.restore()
    text(c, title, x + 380, y + 610, 30, (90, 70, 80))
s.makeImageSnapshot().save(os.path.join(OUT, "locations.png"))
print("ok")
