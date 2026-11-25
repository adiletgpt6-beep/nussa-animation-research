"""Обложка YouTube 1280x720 и листы персонажей (библиотека). python make_art.py OUT_DIR"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, d) for d in ("engine", "characters", "backgrounds")]
import skia, numpy as np
from canvas import paint, col
from character import Character
from face import mouth_vec, MOUTH
import alsu, aidar, nuria, hedgehog, roof, props

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def text(c, s, x, y, size, color, outline, ow=0.16, center=True):
    f = skia.Font(skia.Typeface.MakeFromFile(FONT), size)
    w = f.measureText(s)
    xx = x - w / 2 if center else x
    c.drawString(s, xx, y, f, paint(outline, style="stroke", width=size * ow))
    c.drawString(s, xx, y, f, paint(color))


# ---------- обложка
surf = skia.Surface(1920, 1080); c = surf.getCanvas()
P = roof.PRESETS["after_rain"]
c.save(); c.translate(-560, -60); c.scale(1.05, 1.05)
c.drawImage(roof.render_static("after_rain"), 0, 0)
props.sunflower_pot(c, 1640, 1040, 6.0, P, roof.lit, t=0.3, scale=1.45, sparkle=1.0)
Character(nuria.DESIGN).draw(c, dict(x=2010, y=1000, u=150, face=-1, head_yaw=0.45, face_st=dict(mouth=mouth_vec({"SMILE_OPEN": 0.6, "X": 0.4}), squint=0.5)))
c.restore()
Character(aidar.DESIGN).draw(c, dict(x=1380, y=1010, u=150, face=-1, head_yaw=0.45, arm_f=0.6, elbow_f=2.3, hand_f="pinch",
                                     face_st=dict(mouth=mouth_vec({"SMILE_OPEN": 1}), brow_up=0.6, look=(0.4, -0.4))))
Character(alsu.DESIGN).draw(c, dict(x=700, y=1150, u=300, face=1, head_yaw=0.3, arm_n=-2.6, elbow_n=0.4, hand_n="open",
                                    face_st=dict(mouth=mouth_vec({"SMILE_OPEN": 1}), wide=0.6, brow_up=0.7, look=(0.5, -0.5))))
hedgehog.draw(c, 1180, 1060, 170, face=-1, sniff=0.3)
grad = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 380)], [col((255, 255, 255), 0.55), col((255, 255, 255), 0.0)], [0, 1])
gp = skia.Paint(); gp.setShader(grad); c.drawRect(skia.Rect(0, 0, 1920, 380), gp)
text(c, "Семечко,", 520, 165, 150, (255, 214, 60), (110, 50, 30))
text(c, "которое не спешило", 700, 300, 104, (255, 255, 255), (90, 50, 60))
text(c, "САД НА КРЫШЕ", 1560, 1050, 64, (255, 255, 255), (60, 110, 60), center=True)
img = surf.makeImageSnapshot().resize(1280, 720)
img.save(os.path.join(OUT, "thumbnail_1280x720.png"))

# ---------- листы персонажей
def sheet(mod, name, u):
    ch = Character(mod.DESIGN)
    s = skia.Surface(2400, 1500); cc = s.getCanvas(); cc.clear(col((246, 242, 234)))
    text(cc, name, 1200, 90, 70, (80, 60, 70), (246, 242, 234), ow=0.0)
    # повороты головы и стороны
    for i, (yaw, face) in enumerate(((0.0, 1), (0.45, 1), (0.9, 1), (0.45, -1))):
        ch.draw(cc, dict(x=260 + i * 520, y=760, u=u, face=face, head_yaw=yaw))
    # эмоции
    emos = [("радость", dict(mouth=mouth_vec({"SMILE_OPEN": 1}), squint=0.5)), ("удивление", dict(mouth=mouth_vec({"GASP": 1}), wide=1, brow_up=1)),
            ("грусть", dict(mouth=mouth_vec({"CRY": 1}), brow_inner=1, look=(0, 0.5))), ("сердится", dict(mouth=mouth_vec({"X": 1}), brow_inner=-0.8)),
            ("хитрость", dict(mouth=mouth_vec({"X": 1}), brow_asym=0.8, squint=0.3)), ("сон", dict(mouth=mouth_vec({"X": 1}), blink=1.0))]
    for i, (lab, st) in enumerate(emos):
        x = 200 + i * 380
        cc.save(); cc.translate(x, 1250); cc.scale(1.0, 1.0)
        from face import draw_face
        R = 120
        cc.drawCircle(0, 0, R, paint(mod.DESIGN.skin))
        draw_face(cc, R, mod.DESIGN.face, st, 0.2)
        cc.restore()
        text(cc, lab, x, 1440, 34, (90, 80, 90), (246, 242, 234), ow=0.0)
    s.makeImageSnapshot().save(os.path.join(OUT, f"sheet_{mod.DESIGN.name}.png"))


sheet(alsu, "Алсу, 6 лет", 190)
sheet(aidar, "Айдар, 9 лет", 175)
sheet(nuria, "Бабушка Нурия, 68 лет", 165)

# ---------- формы рта (виземы)
s = skia.Surface(2400, 900); cc = s.getCanvas(); cc.clear(col((246, 242, 234)))
from face import draw_mouth
keys = ["X", "MBP", "A", "O", "U", "I", "E", "Y", "FV", "S", "SH", "T", "K", "R"]
for i, k in enumerate(keys):
    x, y = 160 + (i % 7) * 330, 260 + (i // 7) * 380
    cc.drawCircle(x, y, 120, paint(alsu.DESIGN.skin))
    draw_mouth(cc, x, y + 20, 160, np.array(MOUTH[k]), alsu.DESIGN.face, 0.0)
    text(cc, k, x, y + 175, 40, (90, 80, 90), (246, 242, 234), ow=0.0)
s.makeImageSnapshot().save(os.path.join(OUT, "mouth_chart.png"))
print("ok")
