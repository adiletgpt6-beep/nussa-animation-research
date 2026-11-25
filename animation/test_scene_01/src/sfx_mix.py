"""Процедурные звуковые эффекты + сведение (без музыки).

Все звуки синтезируются кодом (numpy/scipy) — внешних библиотек звуков и лицензий нет.
Запуск: python sfx_mix.py AUDIO_DIR EVENTS_JSON OUT_WAV
"""
import json, sys, os
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
DUR = 19.3
rng = np.random.default_rng(7)


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def lp(x, hi, order=2):
    return sosfilt(butter(order, hi, btype="low", fs=SR, output="sos"), x)


def hp(x, lo, order=2):
    return sosfilt(butter(order, lo, btype="high", fs=SR, output="sos"), x)


def env(n, a, d):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / max(a, 1e-4))) * np.exp(-t / d)


def noise(n):
    return rng.standard_normal(n)


def footstep(kind):
    if kind == "run":
        n = int(0.14 * SR)
        x = bp(noise(n), 250, 4000) * env(n, 0.001, 0.025) * 0.9
        t = np.arange(n) / SR
        x += np.sin(2 * np.pi * 95 * t) * env(n, 0.002, 0.04) * 0.8
        return x
    if kind == "walk":
        n = int(0.16 * SR)
        x = bp(noise(n), 200, 3000) * env(n, 0.002, 0.03) * 0.6
        t = np.arange(n) / SR
        x += np.sin(2 * np.pi * 85 * t) * env(n, 0.003, 0.05) * 0.5
        return x
    n = int(0.28 * SR)  # шарканье (бабушка, переступание)
    x = bp(noise(n), 300, 2500) * np.hanning(n) ** 1.5 * 0.35
    x[: int(0.06 * SR)] += bp(noise(int(0.06 * SR)), 150, 1500) * env(int(0.06 * SR), 0.002, 0.015) * 0.5
    return x


def squeak():
    n = int(0.09 * SR); t = np.arange(n) / SR
    f = 2600 + 700 * t / t[-1]
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(n) * 0.10


def bounce(speed):
    n = int(0.35 * SR); t = np.arange(n) / SR
    a = min(1.0, speed / 3.0)
    x = (np.sin(2 * np.pi * 150 * t) * 0.8 + np.sin(2 * np.pi * 330 * t) * 0.35 + np.sin(2 * np.pi * 620 * t) * 0.12) * env(n, 0.001, 0.07)
    x += bp(noise(n), 800, 5000) * env(n, 0.0005, 0.006) * 0.6
    return x * a * 0.9


def rustle(dur, amount=1.0):
    n = int(dur * SR)
    x = bp(noise(n), 1200, 7000)
    crack = (rng.random(n) < 0.004).astype(float)
    crack = np.convolve(crack, np.exp(-np.arange(200) / 30), mode="same")
    am = lp(np.abs(noise(n)), 25) * 4
    y = x * (0.25 + am) * (0.3 + crack) * np.hanning(n) ** 0.5
    return y / (np.abs(y).max() + 1e-9) * 0.35 * amount


def thud(gain=0.6):
    n = int(0.25 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 70 * t) * env(n, 0.003, 0.06) + lp(noise(n), 600) * env(n, 0.002, 0.03) * 0.8) * gain


def beep():
    n = int(0.36 * SR); t = np.arange(n) / SR
    g = ((t > 0.0) & (t < 0.06)) | ((t > 0.14) & (t < 0.20))
    return np.sin(2 * np.pi * 3200 * t) * g * 0.10


def breath(dur, inhale=0.4, gain=0.25, lo=400, hi=3000):
    n = int(dur * SR); t = np.arange(n) / SR
    x = bp(noise(n), lo, hi)
    k = int(inhale * n)
    e = np.concatenate([np.linspace(0, 0.6, k) ** 1.5, np.linspace(1.0, 0, n - k) ** 1.2])
    return x * e * gain


def pat():
    n = int(0.12 * SR)
    return lp(noise(n), 900) * env(n, 0.002, 0.02) * 0.6


def clunk():
    n = int(1.2 * SR); t = np.arange(n) / SR
    x = lp(noise(n), 300) * env(n, 0.003, 0.08) * 1.2
    x += (np.sin(2 * np.pi * 410 * t) * 0.3 + np.sin(2 * np.pi * 663 * t) * 0.2) * env(n, 0.002, 0.35)
    return x * 0.35


def chirp():
    n = int(0.25 * SR); t = np.arange(n) / SR
    f = 3800 + 1500 * np.sin(2 * np.pi * 14 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(n) * 0.03


def reverb_ir(rt=0.65):
    n = int(rt * SR)
    ir = noise(n) * np.exp(-6.9 * np.arange(n) / n)
    ir = lp(ir, 5000)
    return ir / np.sqrt((ir ** 2).sum())


def add(buf, x, t, pan=0.0, gain=1.0):
    i = int(t * SR)
    if i >= buf.shape[0] or i + len(x) <= 0:
        return
    j = min(buf.shape[0], i + len(x))
    seg = x[: j - i] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += seg * l
    buf[i:j, 1] += seg * r


def main():
    audio_dir, events_json, out = sys.argv[1:4]
    ev = json.load(open(events_json))
    lines = json.load(open(os.path.join(audio_dir, "phonemes.json")))
    n = int(DUR * SR)
    dry = np.zeros((n, 2)); sfx = np.zeros((n, 2)); amb = np.zeros((n, 2)); voice = np.zeros((n, 2))
    # голоса
    talk = np.zeros(n)
    for ln in lines:
        y, sr = sf.read(os.path.join(audio_dir, ln["id"] + ".wav"))
        y = hp(y, 90)
        pan = -0.25 if ln["who"] == "amir" else 0.25
        add(voice, y * 0.55, ln["start"], pan)
        i0 = int(ln["start"] * SR); talk[i0:i0 + len(y)] = 1
    # шаги
    for t, kind in ev["amir_steps"]:
        pan = -0.5 if t < 2.0 else -0.25
        add(sfx, footstep(kind), t, pan, 0.55 if kind == "run" else 0.45)
    stops = [t for t, k in ev["amir_steps"] if k != "run"]
    if stops:
        add(sfx, squeak(), stops[0] + 0.02, -0.3, 1.0)
    for t, kind in ev["baba_steps"]:
        add(sfx, footstep("shuffle"), t - 0.12, 0.3, 0.55)
    # мяч
    for t, s in ev["ball_bounces"]:
        add(sfx, bounce(s), t, -0.1, 0.8)
    if ev["ball_bounces"]:
        t0 = ev["ball_bounces"][-1][0]
        nr = int(2.0 * SR)
        roll = lp(noise(nr), 220) * np.linspace(1, 0, nr) ** 2 * 0.25
        add(sfx, roll, t0, 0.0, 0.6)
    # сумка: хват, подъём (содержимое), шорох при ходьбе
    g = ev["bag_grab"]
    add(sfx, rustle(0.45, 0.8), g - 0.05, -0.1)
    add(sfx, rustle(0.6, 1.0), g + 0.25, -0.1)
    add(sfx, thud(0.35), g + 0.38, -0.1)
    for t, kind in ev["amir_steps"]:
        if t > g + 1.0:
            add(sfx, rustle(0.25, 0.5), t, -0.2)
    # часы, вздох, похлопывания
    add(sfx, beep(), ev["watch_beep"], -0.2)
    s0, s1 = ev["sigh"]
    add(sfx, breath(s1 - s0 + 0.2, inhale=0.35, gain=0.22, lo=350, hi=2600), s0, -0.25)
    for t in ev["pats"]:
        add(sfx, pat(), t, 0.0, 0.8)
    # тяжёлое дыхание: бабушка (подъём без лифта), Амир (после бега)
    t = 0.2
    while t < 3.4:
        add(sfx, breath(1.2, inhale=0.45, gain=0.10, lo=300, hi=2200), t, 0.3); t += 1.45
    t = 2.75
    while t < 5.2:
        add(sfx, breath(0.65, inhale=0.4, gain=0.07, lo=500, hi=3500), t, -0.25); t += 0.85
    # лифт: глухой лязг в начале
    add(sfx, clunk(), 0.15, 0.5, 0.9)
    # атмосфера подъезда
    room = lp(noise(n), 180) * 0.012
    traffic = bp(noise(n), 120, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * np.arange(n) / SR / 7.0)) * 0.006
    amb[:, 0] += room + traffic * 0.8
    amb[:, 1] += lp(noise(n), 180) * 0.012 + traffic
    for t in (5.6, 12.3, 16.9):
        add(amb, chirp(), t, 0.1)
    # эхо подъезда
    ir = reverb_ir(0.7)
    wet = np.zeros_like(sfx)
    for c in range(2):
        wet[:, c] = fftconvolve(sfx[:, c] * 0.25 + voice[:, c] * 0.10, ir)[:n]
    # лёгкое приглушение шумов под речью
    duck = 1 - 0.35 * lp(talk, 8)
    mix = voice + (sfx + wet * 0.6) * duck[:, None] + amb
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.7
    sf.write(out, mix.astype(np.float32), SR)
    print("written", out, mix.shape)


if __name__ == "__main__":
    main()
