"""Рендер серии 1 (версия 2). python render_ep.py VOICE_DIR OUT_MP4 [t0 t1] [scale]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "engine"), HERE]
import episode as ep
from render import render
vdir, out = sys.argv[1:3]
E = ep.build(vdir)
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
t1 = float(sys.argv[4]) if len(sys.argv) > 4 else E.meta["end"]
sc = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
print("seconds", render(E, out, int(t0 * 30), min(E.n_frames, int(t1 * 30)), preview_scale=sc, log_every=300))
