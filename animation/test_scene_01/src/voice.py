"""Синтез русских реплик (Piper TTS, бесплатно, локально) с таймингом фонем.

Запуск: python voice.py CONFIG_DIR VOICES_DIR OUT_DIR
Выход:  OUT_DIR/L*.wav (48 кГц), OUT_DIR/phonemes.json — фонемы с абсолютным временем
        (используется для lip sync), OUT_DIR/voice_report.json — длительности и высота тона.

Высота голоса меняется передискретизацией (без фазового вокодера): длительность заранее
компенсируется параметром length_scale, поэтому темп речи остаётся заданным.
"""
import json, sys, os
import numpy as np, soundfile as sf
from math import gcd
from scipy.signal import resample_poly
from piper import PiperVoice, SynthesisConfig

SR = 48000


def synth(voice, text, length_scale):
    cfg = SynthesisConfig(length_scale=length_scale, noise_scale=0.6, noise_w_scale=0.7)
    audio, phon = [], []
    t = 0.0
    for ch in voice.synthesize(text, syn_config=cfg, include_alignments=True):
        sr = ch.sample_rate
        for a in ch.phoneme_alignments:
            d = float(a.num_samples) / sr
            phon.append([a.phoneme, round(t, 4), round(t + d, 4)])
            t += d
        audio.append(ch.audio_float_array)
    return np.concatenate(audio), sr, phon


def shift(y, sr, semitones):
    """Pitch и форманты вверх/вниз на semitones; длительность делится на r."""
    r = 2 ** (semitones / 12)
    # хотим: воспроизведение при SR, высота ×r  ->  пересэмплировать sr -> SR/r
    target = int(round(SR / r))
    g = gcd(sr, target)
    return resample_poly(y, target // g, sr // g).astype(np.float32), r


def f0_median(y):
    import librosa
    f0, vf, _ = librosa.pyin(y, fmin=70, fmax=500, sr=SR, frame_length=2048)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if len(f0) else None


def main():
    cfg_dir, voices_dir, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    cfg = json.load(open(os.path.join(cfg_dir, "dialogue.json")))
    loaded = {}
    timeline, report = [], []
    for ln in cfg["lines"]:
        vc = cfg["voices"][ln["who"]]
        if vc["model"] not in loaded:
            loaded[vc["model"]] = PiperVoice.load(os.path.join(voices_dir, vc["model"] + ".onnx"), include_alignments=True)
        st = vc.get("pitch_semitones", 0.0)
        r = 2 ** (st / 12)
        y, sr, phon = synth(loaded[vc["model"]], ln["text"], vc["length_scale"] * r)
        y, r = shift(y, sr, st)
        if vc.get("tremolo"):
            tt = np.arange(len(y)) / SR
            y = y * (1 + vc["tremolo"] * np.sin(2 * np.pi * 5.5 * tt))
        # обрезать тишину по краям, сдвинув фонемы
        env = np.abs(y) > 0.01
        i0 = max(0, int(np.argmax(env)) - int(0.03 * SR))
        i1 = min(len(y), len(y) - int(np.argmax(env[::-1])) + int(0.08 * SR))
        y = y[i0:i1]
        off = i0 / SR
        y = 0.9 * y / (np.abs(y).max() + 1e-9)
        sf.write(os.path.join(out, ln["id"] + ".wav"), y, SR)
        dur = len(y) / SR
        ph = []
        for p, a, b in phon:
            a, b = a / r - off, b / r - off
            if b <= 0 or a >= dur:
                continue
            ph.append({"ph": p, "s": round(ln["start"] + max(a, 0), 4), "e": round(ln["start"] + min(b, dur), 4)})
        timeline.append({**ln, "dur": round(dur, 3), "end": round(ln["start"] + dur, 3), "phonemes": ph})
        report.append({"id": ln["id"], "who": ln["who"], "dur_s": round(dur, 2), "f0_median_hz": round(f0_median(y) or 0, 1)})
        print(ln["id"], ln["who"], round(dur, 2), "s", flush=True)
    for a, b in zip(timeline, timeline[1:]):
        if a["end"] > b["start"] - 0.15:
            print("WARNING overlap/short gap", a["id"], a["end"], b["id"], b["start"])
    json.dump(timeline, open(os.path.join(out, "phonemes.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(report, open(os.path.join(out, "voice_report.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
