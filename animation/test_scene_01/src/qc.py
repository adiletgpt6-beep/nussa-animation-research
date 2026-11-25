"""Автоматическая проверка готового MP4 (QC) — по ТЗ и приёмочным тестам Gate 5.

python qc.py VIDEO.mp4 ANIM_QC.json DIALOGUE_JSON OUT_JSON [--asr]
Проверяет: формат и длительность, громкость, отсутствие музыки (классификатор AudioSet AST),
«замёрзшие» и чёрные кадры, lip sync (смыкание губ на м/б/п по данным анимации), моргания,
скольжение стоп, разборчивость русской речи (faster-whisper, опционально).
"""
import json, re, subprocess, sys, os
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research", "pipeline"))


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,pix_fmt:format=duration",
                        "-of", "json", p], capture_output=True, text=True)
    return json.loads(r.stdout)


def loud(p):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    g = lambda pat: float(re.findall(pat, r)[-1])
    return {"integrated_lufs": g(r"I:\s+(-?[\d.]+) LUFS"), "true_peak_dbfs": g(r"Peak:\s+(-?[\d.]+) dBFS")}


def frames_stats(p):
    w, h = 320, 180
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.int16)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    still = d < 0.15
    run = best = 0
    for s in still:
        run = run + 1 if s else 0
        best = max(best, run)
    return {"frames": int(len(f)), "longest_frozen_run_frames": int(best), "black_frames": int((f.mean(axis=(1, 2)) < 8).sum()),
            "share_pairs_with_motion": round(float((d >= 0.5).mean()), 3)}


def music_check(p):
    import soundfile as sf
    from audio_analysis import tag_audio
    tmp = p + ".16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ac", "1", "-ar", "16000", tmp], check=True)
    wav, sr = sf.read(tmp)
    rows = tag_audio(wav, sr, tmp + ".csv", win=5.0, hop=2.5)
    os.remove(tmp); os.remove(tmp + ".csv")
    return {"windows": len(rows), "max_music_prob": round(max(r["music"] for r in rows), 3),
            "share_windows_music_ge_0_5": round(sum(r["music"] >= 0.5 for r in rows) / len(rows), 3),
            "max_speech_prob": round(max(r["speech"] for r in rows), 3)}


def asr(p, script):
    from faster_whisper import WhisperModel
    import soundfile as sf
    tmp = p + ".asr.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ac", "1", "-ar", "16000", tmp], check=True)
    audio, _ = sf.read(tmp, dtype="float32"); os.remove(tmp)
    m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
    segs, _ = m.transcribe(audio, language="ru", beam_size=5, vad_filter=True)
    text = " ".join(s.text.strip() for s in segs)
    norm = lambda s: re.sub(r"[^а-яё ]", " ", s.lower().replace("ё", "е")).split()
    ref, hyp = norm(script), norm(text)
    # WER (Левенштейн по словам)
    D = np.zeros((len(ref) + 1, len(hyp) + 1), int)
    D[:, 0] = range(len(ref) + 1); D[0, :] = range(len(hyp) + 1)
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    return {"asr_text": text, "script_words": len(ref), "wer": round(D[-1, -1] / max(1, len(ref)), 3)}


def lipsync(anim):
    res = {}
    for who in ("amir", "babushka"):
        mbp = anim[who]["mbp_frames"]
        closed = set(anim[who]["mouth_closed_frames"])
        ok = sum(any(f + d in closed for d in (-1, 0, 1)) for f in mbp)
        bl = anim[who]["blinks_s"]
        gaps = np.diff(bl) if len(bl) > 1 else []
        res[who] = {"mbp_phonemes": len(mbp), "mbp_with_lips_closed_pm1frame": ok,
                    "blinks": len(bl), "blink_interval_s_min": round(float(min(gaps)), 2) if len(gaps) else None,
                    "blink_interval_s_max": round(float(max(gaps)), 2) if len(gaps) else None}
    return res


def main():
    video, anim_json, dlg_json, out = sys.argv[1:5]
    anim = json.load(open(anim_json))
    dlg = json.load(open(dlg_json))
    pr = probe(video)
    v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in pr["streams"] if s["codec_type"] == "audio"][0]
    dur = float(pr["format"]["duration"])
    num, den = map(int, v["r_frame_rate"].split("/"))
    rep = {"file": os.path.basename(video),
           "format": {"width": v["width"], "height": v["height"], "fps": num / den, "duration_s": round(dur, 2),
                      "video_codec": v["codec_name"], "pix_fmt": v["pix_fmt"], "audio_codec": a["codec_name"],
                      "audio_rate": int(a["sample_rate"]), "audio_channels": a["channels"]},
           "loudness": loud(video), "frames": frames_stats(video), "lipsync_blinks": lipsync(anim),
           "feet": {"amir": anim["feet_amir"], "babushka": anim["feet_babushka"]}}
    rep["music"] = music_check(video)
    if "--asr" in sys.argv:
        rep["speech_ru"] = asr(video, " ".join(l["text"] for l in dlg["lines"]))
    f = rep["format"]; L = rep["loudness"]; M = rep["music"]; Fr = rep["frames"]
    checks = {
        "resolution_1920x1080": f["width"] == 1920 and f["height"] == 1080,
        "fps_30": abs(f["fps"] - 30) < 1e-6,
        "duration_15_20s": 15.0 <= f["duration_s"] <= 20.0,
        "loudness_-14_-16_LUFS": -16.5 <= L["integrated_lufs"] <= -13.5,
        "true_peak_le_-1dBTP": L["true_peak_dbfs"] <= -0.9,
        "no_music_classifier": M["share_windows_music_ge_0_5"] == 0.0,
        "no_frozen_over_2s": Fr["longest_frozen_run_frames"] < 60,
        "no_black_frames": Fr["black_frames"] == 0,
        "lips_close_on_mbp": all(x["mbp_with_lips_closed_pm1frame"] == x["mbp_phonemes"] for x in rep["lipsync_blinks"].values()),
        "no_foot_sliding": all(x["max_planted_slide_m"] < 0.005 for x in rep["feet"].values()),
    }
    if "speech_ru" in rep:
        checks["speech_intelligible_wer_le_0_35"] = rep["speech_ru"]["wer"] <= 0.35
    checks = {k: bool(v) for k, v in checks.items()}
    rep["checks"] = checks
    rep["passed"] = all(checks.values())
    json.dump(rep, open(out, "w"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(checks, indent=1), "\nPASSED" if rep["passed"] else "\nFAILED")


if __name__ == "__main__":
    main()
