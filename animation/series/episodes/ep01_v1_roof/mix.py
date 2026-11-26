"""Звук серии 1: голоса + шаги из походки + эффекты по событиям + атмосферы. Без музыки.
python mix.py VOICE_DIR OUT_WAV"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "engine"), HERE]
import numpy as np, subprocess
from scipy.signal import fftconvolve, butter, sosfilt
import sfx as S
import episode as ep

SR = 48000


def load_mp3(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def add(buf, x, t, pan=0.0, gain=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]; i = 0
    j = min(len(buf), i + len(x))
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:j, 0] += x[: j - i] * gain * l
    buf[i:j, 1] += x[: j - i] * gain * r


EVENTS = {
    "water_splash": lambda s: S.splash(s, 1.0), "boing": S.boing, "door_open": lambda s: S.door(True, s),
    "door_close": lambda s: S.door(False, s), "door_bang": lambda s: S.door(True, s, bang=True), "jump_whoosh": lambda s: S.whoosh(0.35, s),
    "land": S.land, "dig": S.dig, "pat_soil": S.pat, "sniff": S.sniff, "clock_tick": lambda s: S.tick(6, s), "sneeze_hog": S.sneeze_small,
    "pour": lambda s: S.pour(3.0, s, 1.0), "pour_small": lambda s: S.pour(1.2, s, 0.5), "hog_huff": S.huff, "pot_scrape": S.scrape,
    "cloth": S.cloth, "wings": lambda s: S.wings(s, 1.2), "coo": S.coo, "sparkle": S.sparkle, "time_whoosh": S.time_whoosh,
    "thunder": S.thunder, "umbrella_open": S.umbrella, "rope": S.rope, "seed_drop": S.seed_drop,
    "wind_rise": lambda s: S.amb_wind(4.0, s, 1.2) * np.linspace(0, 1, int(4.0 * SR)),
}
SKIP = {"run_steps", "slow_steps", "crickets", "rain", "birds_morning"}   # покрываются шагами из походки и атмосферами


def main():
    vdir, out = sys.argv[1:3]
    E = ep.build(vdir)
    dur = E.meta["end"]
    n = int(dur * SR) + SR
    voice = np.zeros((n, 2)); fx = np.zeros((n, 2)); amb = np.zeros((n, 2))
    talk = np.zeros(n)
    cam_x = lambda t: E.cam["cx"](t)
    # голоса
    for t, lid, who in E.voice:
        x = load_mp3(os.path.join(vdir, lid + ".mp3"))
        a = E.actors[who]
        pan = max(-0.5, min(0.5, (a.tr["x"](t) - cam_x(t)) / 1800))
        add(voice, x, t, pan, 0.9)
        i = int(t * SR); talk[i:i + len(x)] = 1
    # шаги из походки (касание стопы)
    for name, a in E.actors.items():
        g = a._gait
        prev = (0, 0)
        for f in range(1, len(g)):
            t = f / ep.FPS
            if a.tr["visible"](t) < 0.5:
                continue
            lifts = (g[f][1], g[f][3])
            for k in (0, 1):
                if g[f - 1][1 + 2 * k] > 0.5 and lifts[k] <= 0.01:
                    run = g[f][6]
                    s = S.step_soft(f + k) if name == "nuria" else S.step_kid(f + k, 0.7 + 0.5 * run)
                    pan = max(-0.6, min(0.6, (a.tr["x"](t) - cam_x(t)) / 1500))
                    add(fx, s, t, pan, 0.55 if name != "nuria" else 0.7)
    # события
    for i_, (t, name, gain, pan) in enumerate(E.sfx):
        if name in SKIP or gain <= 0:
            continue
        fn = EVENTS.get(name)
        if fn is None:
            print("нет звука:", name); continue
        add(fx, fn(i_ + 3), t, pan, gain)
    # атмосферы по сценам
    st = E.meta["scene_starts"] + [dur]
    beds = [("morning", 0), ("morning_evening", 1), ("morning", 2), ("morning", 3), ("storm", 4), ("drips", 5)]
    for kind, si in beds:
        a0, a1 = st[si], st[si + 1]
        L = a1 - a0
        if kind == "morning":
            b = S.amb_morning(L, si)
        elif kind == "morning_evening":
            b = S.amb_morning(L, si) * np.linspace(1, 0.3, int(L * SR)) + S.amb_evening(L, si) * np.linspace(0, 1, int(L * SR))
        elif kind == "storm":
            b = S.amb_wind(L, si, 1.0) + S.amb_rain(L, si) * np.clip(np.linspace(-1, 3, int(L * SR)), 0, 1)
        else:
            b = S.amb_drips(L, si)
        fade = np.minimum(1, np.minimum(np.arange(len(b)) / (0.5 * SR), (len(b) - np.arange(len(b))) / (0.5 * SR)))
        add(amb, b * fade, a0, 0.0, 1.0)
        add(amb, np.roll(b, 2400) * fade, a0, 0.4, 0.5)
    # лёгкая «комната» на голос (открытая крыша — короткий отзвук)
    ir = np.random.default_rng(1).standard_normal(int(0.25 * SR)) * np.exp(-np.arange(int(0.25 * SR)) / (0.05 * SR))
    ir /= np.sqrt((ir ** 2).sum())
    for c in range(2):
        voice[:, c] += fftconvolve(voice[:, c], ir)[:n] * 0.06
    duck = 1 - 0.45 * sosfilt(butter(1, 6, "low", fs=SR, output="sos"), talk)
    mix = voice + (fx * 0.9 + amb) * duck[:, None]
    mix = mix[: int(dur * SR)]
    mix /= (np.abs(mix).max() + 1e-9) / 0.8
    import soundfile as sf
    sf.write(out, mix.astype(np.float32), SR)
    print("mix", out, round(dur, 2), "s")


if __name__ == "__main__":
    main()
