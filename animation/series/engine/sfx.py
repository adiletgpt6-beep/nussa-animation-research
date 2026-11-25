"""Процедурная библиотека звуковых эффектов (numpy/scipy, без внешних сэмплов и лицензий).
Каждая функция возвращает моно-сигнал 48 кГц. Вариативность — через seed."""
import math
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def _f(x, lo=None, hi=None, order=2):
    if lo and hi:
        return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)
    if hi:
        return sosfilt(butter(order, hi, "low", fs=SR, output="sos"), x)
    return sosfilt(butter(order, lo, "high", fs=SR, output="sos"), x)


def _env(n, a, d):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / max(a, 1e-4))) * np.exp(-t / d)


def _n(n, seed):
    return np.random.default_rng(seed).standard_normal(n)


def _t(n):
    return np.arange(n) / SR


def step_kid(seed=0, hard=1.0):
    n = int(0.12 * SR)
    x = _f(_n(n, seed), 300, 3500) * _env(n, 0.0008, 0.018) * 0.7 * hard
    x += np.sin(2 * np.pi * (110 + seed % 7 * 4) * _t(n)) * _env(n, 0.002, 0.03) * 0.5 * hard
    return x


def step_soft(seed=0):
    n = int(0.3 * SR)
    x = _f(_n(n, seed), 250, 1800) * np.hanning(n) ** 2 * 0.25
    x[: int(0.05 * SR)] += _f(_n(int(0.05 * SR), seed + 1), 120, 900) * _env(int(0.05 * SR), 0.002, 0.012) * 0.5
    return x


def splash(seed=0, size=1.0):
    n = int(0.9 * SR)
    x = _f(_n(n, seed), 600, 9000) * _env(n, 0.003, 0.18 * size) * 0.9
    drops = np.zeros(n)
    rng = np.random.default_rng(seed)
    for k in range(int(25 * size)):
        i = int(rng.uniform(0.05, 0.8) * SR)
        f = rng.uniform(900, 2600)
        m = int(0.03 * SR)
        if i + m < n:
            drops[i:i + m] += np.sin(2 * np.pi * f * _t(m) * (1 + 3 * _t(m))) * _env(m, 0.0005, 0.008) * 0.25
    return x + drops


def pour(dur=3.0, seed=0, heavy=1.0):
    n = int(dur * SR)
    x = _f(_n(n, seed), 400, 5000)
    am = 0.6 + 0.4 * _f(np.abs(_n(n, seed + 1)), hi=12)
    gl = np.sin(2 * np.pi * (600 + 300 * np.sin(2 * np.pi * 3 * _t(n))) * _t(n)) * 0.08
    e = np.minimum(1, _t(n) / 0.1) * np.minimum(1, (dur - _t(n)) / 0.3)
    return (x * am * 0.35 + gl) * e * heavy


def boing(seed=0):
    n = int(0.45 * SR)
    f = 260 + 220 * np.exp(-_t(n) * 8) * np.sin(2 * np.pi * 9 * _t(n))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.15) * 0.45


def whoosh(dur=0.4, seed=0, up=True):
    n = int(dur * SR)
    x = _n(n, seed)
    out = np.zeros(n)
    seg = n // 8
    for k in range(8):
        lo = 300 + (k if up else 8 - k) * 250
        out[k * seg:(k + 1) * seg] = _f(x[k * seg:(k + 1) * seg], lo, lo * 3)
    return out * np.hanning(n) * 0.4


def land(seed=0):
    n = int(0.25 * SR)
    return (np.sin(2 * np.pi * 80 * _t(n)) * _env(n, 0.002, 0.05) + _f(_n(n, seed), hi=700) * _env(n, 0.001, 0.02) * 0.7) * 0.6


def door(open_=True, seed=0, bang=False):
    n = int(1.2 * SR)
    t = _t(n)
    creak_f = 500 + 300 * np.sin(2 * np.pi * 1.3 * t) + (200 if open_ else -100) * t
    creak = np.sin(2 * np.pi * np.cumsum(creak_f) / SR) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 34 * t))) * 0.07 * np.hanning(n)
    latch = np.zeros(n)
    m = int(0.08 * SR)
    latch[:m] += _f(_n(m, seed), 1500, 6000) * _env(m, 0.0005, 0.01) * 0.6
    x = creak + latch
    if bang or not open_:
        k = int(0.85 * SR) if not open_ else 0
        b = int(0.3 * SR)
        x[k:k + b] += (_f(_n(b, seed + 3), hi=500) * _env(b, 0.001, 0.06) * (1.2 if bang else 0.6))[: n - k]
    return x


def dig(seed=0):
    n = int(0.25 * SR)
    return _f(_n(n, seed), 200, 2500) * _env(n, 0.005, 0.06) * 0.6


def pat(seed=0):
    n = int(0.15 * SR)
    return _f(_n(n, seed), hi=900) * _env(n, 0.002, 0.03) * 0.7


def sniff(seed=0):
    out = np.zeros(int(0.6 * SR))
    for k in range(3):
        m = int(0.09 * SR)
        i = int(k * 0.17 * SR)
        out[i:i + m] += _f(_n(m, seed + k), 1500, 6000) * np.hanning(m) * 0.25
    return out


def sneeze_small(seed=0):
    n = int(0.5 * SR)
    t = _t(n)
    pre = np.sin(2 * np.pi * (700 + 400 * t) * t) * np.exp(-((t - 0.12) / 0.06) ** 2) * 0.15
    burst = _f(_n(n, seed), 800, 7000) * np.exp(-((t - 0.3) / 0.03) ** 2) * 0.9
    return pre + burst


def huff(seed=0):
    n = int(0.35 * SR)
    return _f(_n(n, seed), 400, 3000) * _env(n, 0.01, 0.08) * 0.4


def scrape(seed=0):
    n = int(0.5 * SR)
    t = _t(n)
    x = _f(_n(n, seed), 200, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * 40 * t))
    return x * np.hanning(n) * 0.35


def cloth(seed=0, dur=0.7):
    n = int(dur * SR)
    return _f(_n(n, seed), 1500, 8000) * np.hanning(n) * (0.3 + 0.7 * np.abs(_f(_n(n, seed + 1), hi=20))) * 0.4


def tick(n_ticks=6, seed=0):
    out = np.zeros(int(n_ticks * 0.5 * SR + SR * 0.1))
    for k in range(n_ticks):
        m = int(0.02 * SR); i = int(k * 0.5 * SR)
        out[i:i + m] += np.sin(2 * np.pi * (2200 if k % 2 else 1800) * _t(m)) * _env(m, 0.0003, 0.004) * 0.4
    return out


def wings(seed=0, dur=1.0):
    n = int(dur * SR)
    t = _t(n)
    flap = (np.sin(2 * np.pi * 11 * t) > 0.3).astype(float)
    return _f(_n(n, seed), 300, 3000) * _f(flap, hi=60) * np.hanning(n) * 0.6


def coo(seed=0):
    n = int(0.8 * SR)
    t = _t(n)
    f = 420 + 40 * np.sin(2 * np.pi * 6 * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return x * (np.exp(-((t - 0.2) / 0.12) ** 2) + 0.8 * np.exp(-((t - 0.55) / 0.12) ** 2)) * 0.12


def sparkle(seed=0):
    out = np.zeros(int(1.2 * SR))
    rng = np.random.default_rng(seed)
    for k in range(9):
        m = int(0.25 * SR); i = int(k * 0.09 * SR)
        f = 1800 * 2 ** (rng.integers(0, 12) / 12)
        out[i:i + m] += np.sin(2 * np.pi * f * _t(m)) * _env(m, 0.001, 0.08) * 0.08
    return out


def thunder(seed=0):
    n = int(3.5 * SR)
    t = _t(n)
    x = _f(_n(n, seed), hi=180) * (np.exp(-t / 1.2) * (0.4 + 0.6 * np.abs(_f(_n(n, seed + 1), hi=6))))
    crack = _f(_n(n, seed + 2), 800, 6000) * np.exp(-t / 0.08) * 0.5
    return (x * 3.0 + crack) * 0.8


def rope(seed=0):
    n = int(0.3 * SR)
    return _f(_n(n, seed), 1000, 5000) * np.hanning(n) * 0.3


def umbrella(seed=0):
    n = int(0.5 * SR)
    x = _f(_n(n, seed), 400, 4000) * _env(n, 0.02, 0.12) * 0.6
    m = int(0.06 * SR)
    x[int(0.3 * SR):int(0.3 * SR) + m] += _f(_n(m, seed + 1), 1500, 6000) * _env(m, 0.0005, 0.01)
    return x


def seed_drop(seed=0):
    n = int(0.15 * SR)
    return np.sin(2 * np.pi * 1300 * _t(n)) * _env(n, 0.0005, 0.02) * 0.3


def time_whoosh(seed=0):
    return whoosh(0.8, seed, up=True) * 0.6


# ---- атмосферы (циклы)
def amb_morning(dur, seed=0):
    n = int(dur * SR)
    t = _t(n)
    x = _f(_n(n, seed), 80, 600) * 0.012  # далёкий город
    rng = np.random.default_rng(seed)
    for k in range(int(dur * 1.2)):
        i = int(rng.uniform(0, dur - 1) * SR)
        m = int(rng.uniform(0.15, 0.45) * SR)
        f0 = rng.uniform(2800, 4800)
        tt = _t(m)
        chirp = np.sin(2 * np.pi * np.cumsum(f0 + 900 * np.sin(2 * np.pi * rng.uniform(8, 18) * tt)) / SR) * np.hanning(m) * 0.03
        x[i:i + m] += chirp
    return x


def amb_evening(dur, seed=0):
    n = int(dur * SR)
    t = _t(n)
    x = _f(_n(n, seed), 80, 500) * 0.015
    cr = np.sin(2 * np.pi * 4300 * t) * (np.sin(2 * np.pi * 28 * t) > 0.6) * (np.sin(2 * np.pi * 0.7 * t) > 0) * 0.012
    return x + cr


def amb_wind(dur, seed=0, strength=1.0):
    n = int(dur * SR)
    t = _t(n)
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t) * np.sin(2 * np.pi * 0.11 * t + 1)
    return _f(_n(n, seed), 150, 1200) * mod * 0.18 * strength


def amb_rain(dur, seed=0):
    n = int(dur * SR)
    x = _f(_n(n, seed), 1500, 9000) * 0.08
    rng = np.random.default_rng(seed)
    for k in range(int(dur * 25)):
        i = int(rng.uniform(0, dur - 0.05) * SR); m = int(0.02 * SR)
        x[i:i + m] += _f(_n(m, seed + k), 2000, 7000) * _env(m, 0.0003, 0.004) * 0.15
    return x


def amb_drips(dur, seed=0):
    x = amb_morning(dur, seed) * 1.2
    rng = np.random.default_rng(seed + 9)
    for k in range(int(dur * 2)):
        i = int(rng.uniform(0, dur - 0.1) * SR); m = int(0.06 * SR)
        x[i:i + m] += np.sin(2 * np.pi * rng.uniform(900, 1600) * _t(m) * (1 + 2 * _t(m))) * _env(m, 0.0005, 0.012) * 0.08
    return x
