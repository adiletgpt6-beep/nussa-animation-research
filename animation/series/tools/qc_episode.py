"""QC готовой серии: формат, длительность 4–6 мин, громкость, музыка (AudioSet AST), замёрзшие/чёрные кадры,
распознавание речи (faster-whisper) и сравнение со сценарием. python qc_episode.py MP4 SCRIPT_PY OUT_JSON"""
import sys, os, re, json, importlib.util
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "animation", "test_scene_01", "src"))
sys.path.insert(0, os.path.join(REPO, "research", "pipeline"))
import qc as Q

mp4, script_py, out = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("script", script_py); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
clean = lambda s: re.sub(r"\[[^\]]*\]", "", s).replace("́", "")
script = " ".join(clean(l[3]) for l in S.LINES)
pr = Q.probe(mp4)
v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
a = [s for s in pr["streams"] if s["codec_type"] == "audio"][0]
num, den = map(int, v["r_frame_rate"].split("/"))
def static_runs(p):
    """Полностью статичные участки: ни в одном блоке 20×20 (из 320×180) нет изменений. Отличает «тихий» план
    (двигаются только губы и глаза) от застывшего кадра."""
    import subprocess, numpy as np
    w, h = 320, 180
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.int16)
    d = np.abs(np.diff(f, axis=0)).reshape(-1, h // 20, 20, w // 20, 20).mean(axis=(2, 4)).max(axis=(1, 2))
    still = d < 0.6
    best = run = 0; where = 0.0
    for i, s_ in enumerate(still):
        run = run + 1 if s_ else 0
        if run > best:
            best, where = run, (i - run + 1) / 30
    return {"longest_static_run_frames": int(best), "at_s": round(where, 2)}


rep = {"format": {"width": v["width"], "height": v["height"], "fps": num / den, "duration_s": round(float(pr["format"]["duration"]), 2),
                  "video_codec": v["codec_name"], "audio_codec": a["codec_name"], "audio_rate": int(a["sample_rate"])},
       "loudness": Q.loud(mp4), "frames": Q.frames_stats(mp4), "music": Q.music_check(mp4), "speech_ru": Q.asr(mp4, script), "static": static_runs(mp4)}
f, L, M, Fr, Sp = rep["format"], rep["loudness"], rep["music"], rep["frames"], rep["speech_ru"]
checks = {"1920x1080": f["width"] == 1920 and f["height"] == 1080, "30fps": abs(f["fps"] - 30) < 1e-6,
          "h264_aac": f["video_codec"] == "h264" and f["audio_codec"] == "aac", "duration_4_6_min": 240 <= f["duration_s"] <= 360,
          "loudness_-13_-15_LUFS": -15.0 <= L["integrated_lufs"] <= -13.0, "true_peak_le_-1": L["true_peak_dbfs"] <= -0.95,
          "no_music_classifier": M["share_windows_music_ge_0_5"] == 0.0, "no_static_over_2s": rep["static"]["longest_static_run_frames"] < 60,
          "black_frames_only_in_fades": Fr["black_frames"] < 60, "speech_wer_le_0_35": Sp["wer"] <= 0.35}
rep["checks"] = {k: bool(x) for k, x in checks.items()}
rep["passed"] = all(rep["checks"].values())
json.dump(rep, open(out, "w"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(rep["checks"], indent=1)); print({k: rep[k] for k in ("loudness", "frames", "music", "static")}); print(Sp["wer"])
