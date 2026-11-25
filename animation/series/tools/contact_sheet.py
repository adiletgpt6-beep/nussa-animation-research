"""Контактный лист серии: кадр каждые N секунд в сетке (для визуальной проверки всей серии).
python tools/contact_sheet.py EP_DIR VOICE_DIR OUT_PREFIX [step_s] [t0] [t1]"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ep_dir = os.path.abspath(sys.argv[1])
sys.path[:0] = [os.path.join(ROOT, "engine"), ep_dir]
import skia
from canvas import W, H, paint
import episode as ep
vdir, out = sys.argv[2], sys.argv[3]
step = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
E = ep.build(vdir)
t0 = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
t1 = float(sys.argv[6]) if len(sys.argv) > 6 else E.meta["end"]
times = []
t = t0
while t < t1:
    times.append(t); t += step
cols, sc = 6, 0.25
per = 36
font = skia.Font(skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"), 22)
fr = skia.Surface(int(W * sc), int(H * sc))
for page in range(0, len(times), per):
    chunk = times[page:page + per]
    rows = (len(chunk) + cols - 1) // cols
    sh = skia.Surface(int(W * sc) * cols, int(H * sc) * rows)
    scv = sh.getCanvas(); scv.clear(skia.ColorWHITE)
    for i, tt in enumerate(chunk):
        c = fr.getCanvas(); c.save(); c.scale(sc, sc); E.draw_frame(c, int(tt * 30)); c.restore()
        x, y = (i % cols) * W * sc, (i // cols) * H * sc
        scv.drawImage(fr.makeImageSnapshot(), x, y)
        scv.drawString(f"{tt:.0f}s", x + 6, y + 24, font, paint((255, 255, 255)))
        scv.drawString(f"{tt:.0f}s", x + 5, y + 23, font, paint((20, 20, 20)))
    sh.makeImageSnapshot().save(f"{out}_{page // per:02d}.png")
    print("page", page // per, flush=True)
