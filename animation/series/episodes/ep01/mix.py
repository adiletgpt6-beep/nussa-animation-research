"""Звук серии 1 (версия 2): голоса + шаги из походки (пол/трава) + бытовые эффекты + атмосферы локаций.
Фоновой музыки нет. Тишина — тоже часть атмосферы: атмосферы тихие, под речью приглушаются.
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
    "water_splash": lambda s: S.splash(s, 0.6), "boing": S.boing, "door_open": lambda s: S.door(True, s),
    "door_close": lambda s: S.door(False, s), "jump_whoosh": lambda s: S.whoosh(0.3, s), "land": S.land, "dig": S.dig,
    "pat_soil": S.pat, "sniff": S.sniff, "pour_small": lambda s: S.pour(1.0, s, 0.4), "hog_huff": S.huff, "cloth": S.cloth,
    "wings": lambda s: S.wings(s, 1.0), "coo": S.coo, "sparkle": S.sparkle, "umbrella_open": S.umbrella, "rope": S.rope,
    "seed_drop": S.seed_drop, "slosh": S.slosh, "paper": S.paper, "click": S.click, "scribble": S.scribble, "drips": S.drips,
    "pop_soft": S.pop_soft,
}


def amb_bed(kind, L, seed):
    if kind == "room":
        return S.amb_room(L, seed)
    if kind == "yard_morning":
        return S.amb_morning(L, seed) * 0.8 + S.amb_breeze(L, seed) * 0.5
    if kind == "yard_evening":
        return S.amb_evening(L, seed) * 0.7 + S.amb_morning(L, seed + 5) * 0.25 + S.amb_breeze(L, seed) * 0.4
    if kind == "windy":
        n = int(L * SR)
        rain = S.amb_soft_rain(L, seed) * np.clip(np.linspace(-2.0, 2.0, n), 0, 1)
        return S.amb_breeze(L, seed) * 2.2 + rain
    return np.zeros(int(L * SR))


def main():
    vdir, out = sys.argv[1:3]
    E = ep.build(vdir)
    dur = E.meta["end"]
    n = int(dur * SR) + SR
    voice = np.zeros((n, 2)); fx = np.zeros((n, 2)); amb = np.zeros((n, 2))
    talk = np.zeros(n)
    loc_at = lambda t: E.env["loc"](t).split(":")[0]
    ins_at = lambda t: any(a <= t < b for a, b, _ in E.inserts)
    cam_x = lambda t: E.cam["cx"](t)
    for t, lid, who in E.voice:
        x = load_mp3(os.path.join(vdir, lid + ".mp3"))
        a = E.actors[who]
        pan = 0.0 if ins_at(t) else max(-0.45, min(0.45, (a.tr["x"](t) - cam_x(t)) / 1800))
        add(voice, x, t, pan, 0.9)
        i = int(t * SR); talk[i:i + len(x)] = 1
    # шаги — по касанию стопы; на траве тише и мягче, во время вставок не слышны
    for name, a in E.actors.items():
        g = a._gait
        for f in range(1, len(g)):
            t = f / ep.FPS
            if a.tr["visible"](t) < 0.5 or ins_at(t):
                continue
            for k in (0, 1):
                if g[f - 1][1 + 2 * k] > 0.5 and g[f][1 + 2 * k] <= 0.01:
                    run = g[f][6]
                    yard = loc_at(t) == "yard"
                    s = S.step_soft(f + k) if (name == "leyla" or yard) else S.step_kid(f + k, 0.6 + 0.4 * run)
                    pan = max(-0.6, min(0.6, (a.tr["x"](t) - cam_x(t)) / 1500))
                    gain = (0.45 if yard else 0.42) * (0.8 if name == "leyla" else 1.0)
                    add(fx, s, t, pan, gain)
    for i_, (t, name, gain, pan) in enumerate(E.sfx):
        if gain <= 0:
            continue
        fn = EVENTS.get(name)
        if fn is None:
            print("нет звука:", name); continue
        add(fx, fn(i_ + 3), t, pan, gain * 0.85)
    # атмосферы по локациям, с мягкими переходами
    seg = sorted(E.amb) + [(dur, None)]
    for (a0, kind), (a1, _) in zip(seg, seg[1:]):
        L = a1 - a0
        if L <= 0.05:
            continue
        b = amb_bed(kind, L + 0.6, int(a0))
        m = len(b)
        fade = np.minimum(1, np.minimum(np.arange(m) / (0.35 * SR), (m - np.arange(m)) / (0.6 * SR)))
        add(amb, b * fade, a0 - 0.1, -0.2, 0.9)
        add(amb, np.roll(b, 2400) * fade, a0 - 0.1, 0.3, 0.45)
    # «комната» на голос: в доме чуть больше отзвука, во дворе почти сухо
    ir = np.random.default_rng(1).standard_normal(int(0.3 * SR)) * np.exp(-np.arange(int(0.3 * SR)) / (0.06 * SR))
    ir /= np.sqrt((ir ** 2).sum())
    wet = np.array([0.09 if loc_at(i / SR) != "yard" else 0.035 for i in range(0, n, SR // 10)])
    wet = np.repeat(wet, SR // 10)[:n]
    for c in range(2):
        voice[:, c] += fftconvolve(voice[:, c], ir)[:n] * wet[: n]
    duck = 1 - 0.5 * sosfilt(butter(1, 5, "low", fs=SR, output="sos"), talk)
    mix = voice + (fx * 0.9 + amb) * duck[:, None]
    mix = mix[: int(dur * SR)]
    mix /= (np.abs(mix).max() + 1e-9) / 0.8
    import soundfile as sf
    sf.write(out, mix.astype(np.float32), SR)
    print("mix", out, round(dur, 2), "s")


if __name__ == "__main__":
    main()
