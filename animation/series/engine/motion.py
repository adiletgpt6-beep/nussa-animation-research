"""Движение: каналы с ключами (slow in/out), пружины (follow-through), моргания, синхронизация губ
по таймингам символов ElevenLabs (русские буквы -> виземы), генератор шагов (ходьба/бег)."""
import math, random
import numpy as np

FPS = 30


def ease(x, kind="inout"):
    x = min(1.0, max(0.0, x))
    if kind == "linear":
        return x
    if kind == "in":
        return x * x * x
    if kind == "out":
        return 1 - (1 - x) ** 3
    if kind == "back":  # с перелётом (overshoot) — follow through
        s = 1.70158
        x -= 1
        return x * x * ((s + 1) * x + s) + 1
    return x * x * (3 - 2 * x) if kind == "smooth" else (x * x * x * (x * (x * 6 - 15) + 10))


class Track:
    """Ключи (t, value, ease). Значение между ключами — по кривой следующего ключа."""

    def __init__(self, default=0.0):
        self.k = []
        self.default = default

    def key(self, t, v, e="inout"):
        self.k.append((t, v, e))
        self.k.sort(key=lambda a: a[0])
        return self

    def hold(self, t):
        self.key(t, self(t), "linear")

    def __call__(self, t):
        k = self.k
        if not k:
            return self.default
        if t <= k[0][0]:
            return k[0][1]
        for (t0, v0, _), (t1, v1, e) in zip(k, k[1:]):
            if t0 <= t <= t1:
                if t1 - t0 < 1e-6:
                    return v1
                s = ease((t - t0) / (t1 - t0), e)
                if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                    return v0 + (v1 - v0) * s
                return v1 if s > 0.5 else v0
        return k[-1][1]


class Spring:
    """Затухающая пружина для вторичного движения (волосы, платок, подол)."""

    def __init__(self, k=60.0, damp=7.0):
        self.k, self.d = k, damp
        self.x = 0.0
        self.v = 0.0

    def step(self, force, dt=1 / FPS):
        a = -self.k * self.x - self.d * self.v + force
        self.v += a * dt
        self.x += self.v * dt
        return self.x


def blink_times(dur, seed, forced=()):
    rnd = random.Random(seed)
    t = rnd.uniform(0.6, 1.8)
    out = []
    while t < dur:
        out.append(t)
        t += rnd.uniform(2.2, 4.6)
    for f in forced:
        if all(abs(f - x) > 0.7 for x in out):
            out.append(f)
    return sorted(out)


def blink_value(t, times):
    v = 0.0
    for b in times:
        d = t - b
        if 0 <= d < 0.22:
            v = max(v, [0.5, 1.0, 1.0, 0.75, 0.4, 0.15, 0.0][min(6, int(d * FPS))])
    return v


# ---------------------------------------------------------------- lip sync
LETTER_VIS = {}
for ch in "аяА": LETTER_VIS[ch] = "A"
for ch in "оё": LETTER_VIS[ch] = "O"
for ch in "ую": LETTER_VIS[ch] = "U"
for ch in "иы": LETTER_VIS[ch] = "I"
for ch in "эе": LETTER_VIS[ch] = "E"
for ch in "мбп": LETTER_VIS[ch] = "MBP"
for ch in "фв": LETTER_VIS[ch] = "FV"
for ch in "сзц": LETTER_VIS[ch] = "S"
for ch in "шщжч": LETTER_VIS[ch] = "SH"
for ch in "тднл": LETTER_VIS[ch] = "T"
LETTER_VIS["р"] = "R"
for ch in "кгх": LETTER_VIS[ch] = "K"
LETTER_VIS["й"] = "I"
VOWELS = set("аяоёуюиыэе")


def strip_tags(chars, starts, ends):
    """Убирает [теги] из выравнивания ElevenLabs."""
    out = []
    inside = False
    for c, s, e in zip(chars, starts, ends):
        if c == "[":
            inside = True
            continue
        if c == "]":
            inside = False
            continue
        if not inside:
            out.append((c, s, e))
    return out


def viseme_events(alignment, t0, lead=0.04):
    """-> список (start, end, viseme, is_vowel) в абсолютном времени серии."""
    ch = strip_tags(alignment["characters"], alignment["character_start_times_seconds"], alignment["character_end_times_seconds"])
    ev = []
    for c, s, e in ch:
        lc = c.lower()
        if lc in ("ь", "ъ", "́"):
            if ev:
                ev[-1] = (ev[-1][0], e + t0 - lead, ev[-1][2], ev[-1][3])
            continue
        v = LETTER_VIS.get(lc)
        if v is None:
            v = "X" if lc in " .,!?…—-:;\"'" else None
        if v is None:
            continue
        ev.append((s + t0 - lead, e + t0 - lead, v, lc in VOWELS))
    # схлопнуть пробелы короче 0.1 с (не закрывать рот между словами)
    out = []
    for e_ in ev:
        if e_[2] == "X" and e_[1] - e_[0] < 0.12:
            continue
        out.append(e_)
    return out


def mouth_weights(t, events, window=0.045):
    """Веса визем в момент t со сглаживанием (коартикуляция); м/б/п — гарантированное смыкание."""
    w = {}
    for s, e, v, vowel in events:
        if e < t - 0.15 or s > t + 0.15:
            continue
        mid = (s + e) / 2
        half = max((e - s) / 2, 0.025)
        d = abs(t - mid)
        k = max(0.0, 1.0 - max(0.0, d - half) / window)
        if k <= 0:
            continue
        k *= 1.15 if vowel else 0.85
        if v == "MBP" and s - 0.012 <= t <= e + 0.012:
            return {"MBP": 1.0}
        w[v] = w.get(v, 0) + k
    if not w:
        return {"X": 1.0}
    return w


# ---------------------------------------------------------------- шаги

def gait_track(xs, dt=1 / FPS, run_thr=180.0, step_px=(70, 120), hip_w=0.0):
    """xs: позиции корня по кадрам (px мира, вдоль x). Возвращает для каждого кадра:
    (foot_near_x, foot_near_lift, foot_far_x, foot_far_lift, phase, speed, run_blend)."""
    n = len(xs)
    v = np.gradient(np.array(xs, float)) / dt
    vs = np.convolve(np.abs(v), np.ones(5) / 5, mode="same")
    phase = 0.0
    feet = {0: xs[0], 1: xs[0]}
    out = []
    plant = {0: xs[0] + 8, 1: xs[0] - 8}
    swing = {0: None, 1: None}
    for i in range(n):
        sp = vs[i]
        runb = min(1.0, max(0.0, (sp - run_thr * 0.7) / (run_thr * 0.6)))
        stride = step_px[0] + (step_px[1] - step_px[0]) * runb
        if sp > 8:
            phase += sp * dt / (2 * stride)
        res = []
        for leg in (0, 1):
            ph = (phase + 0.5 * leg) % 1.0
            stance = 0.6 - 0.22 * runb
            direction = 1 if v[i] >= 0 else -1
            if sp <= 8:
                # стоим: стопы подтягиваются к корню
                target = xs[i] + (8 if leg == 0 else -8)
                plant[leg] += (target - plant[leg]) * 0.25
                res += [plant[leg], 0.0]
                continue
            if ph < stance:
                if swing[leg] is not None:
                    plant[leg] = swing[leg]
                    swing[leg] = None
                res += [plant[leg], 0.0]
            else:
                s = (ph - stance) / (1 - stance)
                land = xs[i] + direction * stride * 0.45 * (1 - s) + direction * stride * 0.45 * s * 0 + direction * stride * 0.5
                land = xs[i] + direction * stride * (0.55 - 0.1 * runb) * 1.0 + direction * sp * dt * (1 - s) * (1 - stance) / dt * 0
                x0 = plant[leg]
                fx = x0 + (land - x0) * (s * s * (3 - 2 * s))
                swing[leg] = fx
                res += [fx, math.sin(math.pi * s) * (14 + 22 * runb)]
        out.append((res[0], res[1], res[2], res[3], phase, sp, runb))
    return out
