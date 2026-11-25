#!/usr/bin/env python3
"""Audio analysis of a locally available video (free, local models only; no paid APIs).

Usage:
  audio_analysis.py VIDEO SEGMENTS_JSON OUT_DIR [--skip-asr] [--asr-model small] [--reuse]

Writes to OUT_DIR (keep OUT_DIR outside git; only the *_summary.json is meant to be committed):
  audio_tags.csv        per 2.5 s window: speech / music / laughter / SFX-like probabilities
                        (AudioSet AST classifier, MIT/ast-finetuned-audioset-10-10-0.4593)
  asr_words.json        word timestamps from faster-whisper (LOCAL ONLY - third-party dialogue)
  audio_summary.json    per-segment aggregates: loudness (EBU R128), music/speech shares,
                        words per minute, speech coverage, pauses. Numbers only.
"""
import argparse, json, os, re, subprocess
import numpy as np
import soundfile as sf

SFX_HINTS = ("Door", "Knock", "Footsteps", "Walk", "Slam", "Thump", "Bang", "Whoosh", "Boing",
             "Pop", "Click", "Tick", "Rain", "Thunder", "Wind", "Water", "Cat", "Meow", "Bird",
             "Vehicle", "Engine", "Telephone", "Ringtone", "Glass", "Dishes", "Cutlery", "Squeak",
             "Splash", "Crash", "Breaking", "Zipper", "Sneeze", "Cough", "Yawn", "Snoring")


def ebur128(video, start, dur):
    r = subprocess.run(["ffmpeg", "-nostats", "-ss", str(start), "-t", str(dur), "-i", video,
                        "-vn", "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    g = lambda p: (float(m[-1]) if (m := re.findall(p, r)) else None)
    return {"integrated_lufs": g(r"I:\s+(-?[\d.]+) LUFS"), "lra_lu": g(r"LRA:\s+([\d.]+) LU"),
            "true_peak_dbfs": g(r"Peak:\s+(-?[\d.]+) dBFS")}


def tag_audio(wav, sr, out_csv, win=5.0, hop=2.5):
    import torch
    from transformers import ASTFeatureExtractor, ASTForAudioClassification
    name = "MIT/ast-finetuned-audioset-10-10-0.4593"
    fe = ASTFeatureExtractor.from_pretrained(name)
    model = ASTForAudioClassification.from_pretrained(name).eval()
    labels = model.config.id2label
    idx = {l: i for i, l in labels.items()}
    speech_i = [idx[k] for k in ("Speech", "Child speech, kid speaking", "Conversation", "Narration, monologue") if k in idx]
    music_i = [i for i, l in labels.items() if l in ("Music", "Musical instrument", "Background music", "Theme music",
                                                     "Piano", "Guitar", "Synthesizer", "Percussion", "Drum",
                                                     "Orchestra", "Song", "Singing", "Children's music")]
    laugh_i = [i for i, l in labels.items() if "Laugh" in l or "Giggle" in l or "Chuckle" in l]
    sfx_i = [i for i, l in labels.items() if any(h.lower() in l.lower() for h in SFX_HINTS)]
    rows = []
    n = int(win * sr); h = int(hop * sr)
    batch, starts = [], []
    def flush():
        inp = fe(batch, sampling_rate=sr, return_tensors="pt")
        with torch.no_grad():
            p = torch.sigmoid(model(**inp).logits).numpy()
        for t, pr in zip(starts, p):
            top = np.argsort(-pr)[:3]
            rows.append({"t": round(t, 2), "speech": round(float(pr[speech_i].max()), 3),
                         "music": round(float(pr[music_i].max()), 3), "laughter": round(float(pr[laugh_i].max()), 3),
                         "sfx": round(float(pr[sfx_i].max()), 3),
                         "top": "|".join(f"{labels[i]}:{pr[i]:.2f}" for i in top)})
    for s in range(0, max(1, len(wav) - n + 1), h):
        batch.append(wav[s:s + n]); starts.append(s / sr)
        if len(batch) == 16:
            flush(); batch, starts = [], []
            if int(s / sr) % 600 < hop:
                print(f"tagged {s / sr:.0f}s", flush=True)
    if batch:
        flush()
    import csv
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return rows


def run_asr(wav16_path, model_name, out_json):
    from faster_whisper import WhisperModel
    m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4)
    audio, _sr = sf.read(wav16_path, dtype="float32")  # pass array: some PyAV versions reject paths here
    segs, info = m.transcribe(audio, language="id", word_timestamps=True, vad_filter=True, beam_size=1)
    words = []
    for s in segs:
        for w in (s.words or []):
            words.append({"s": round(w.start, 2), "e": round(w.end, 2), "w": w.word.strip(), "p": round(w.probability, 2)})
    json.dump({"language": info.language, "words": words}, open(out_json, "w"), ensure_ascii=False)
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("segments"); ap.add_argument("out_dir")
    ap.add_argument("--skip-asr", action="store_true"); ap.add_argument("--asr-model", default="small")
    ap.add_argument("--reuse", action="store_true", help="reuse existing audio_tags.csv / asr_words.json in OUT_DIR")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    wavp = os.path.join(a.out_dir, "audio16k.wav")
    if not os.path.exists(wavp):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-ac", "1", "-ar", "16000", wavp], check=True)
    wav, sr = sf.read(wavp)
    segs = json.load(open(a.segments))
    tags_csv = os.path.join(a.out_dir, "audio_tags.csv")
    asr_json = os.path.join(a.out_dir, "asr_words.json")
    if a.reuse and os.path.exists(tags_csv):
        import csv
        tags = [{k: (v if k == "top" else float(v)) for k, v in r.items()} for r in csv.DictReader(open(tags_csv))]
    else:
        tags = tag_audio(wav, sr, tags_csv)
    print("tagging done", flush=True)
    if a.skip_asr:
        words = []
    elif a.reuse and os.path.exists(asr_json):
        words = json.load(open(asr_json))["words"]
    else:
        words = run_asr(wavp, a.asr_model, asr_json)
    print("asr done", len(words), flush=True)
    summary = {"method": {"tagger": "MIT/ast-finetuned-audioset-10-10-0.4593 (5 s windows, 2.5 s hop, sigmoid probs)",
                          "asr": None if a.skip_asr else f"faster-whisper {a.asr_model}, language=id, VAD, word timestamps",
                          "loudness": "ffmpeg ebur128"}, "segments": []}
    for s in segs:
        st, en = s["start"], s["end"]; dur = en - st
        tw = [t for t in tags if st <= t["t"] and t["t"] + 5 <= en + 0.1]
        ww = [w for w in words if st <= w["s"] < en]
        speech_t = sum(min(w["e"], en) - w["s"] for w in ww)
        gaps = [b["s"] - a_["e"] for a_, b in zip(ww, ww[1:])]
        frac = lambda k, th: round(sum(t[k] >= th for t in tw) / len(tw), 3) if tw else None
        summary["segments"].append({
            "id": s["id"], "title": s["title"], "duration_s": round(dur, 1),
            "loudness": ebur128(a.video, st, dur),
            "windows": len(tw),
            "share_windows_music_ge_0_3": frac("music", 0.3), "share_windows_music_ge_0_5": frac("music", 0.5),
            "share_windows_speech_ge_0_5": frac("speech", 0.5), "share_windows_laughter_ge_0_3": frac("laughter", 0.3),
            "share_windows_sfx_ge_0_3": frac("sfx", 0.3),
            "asr_words": len(ww) if words else None,
            "asr_wpm_full": round(60 * len(ww) / dur, 1) if words else None,
            "asr_speech_coverage_pct": round(100 * speech_t / dur, 1) if words else None,
            "asr_pauses_ge_2s": sum(g >= 2 for g in gaps) if words else None,
            "first_word_s_from_segment_start": round(ww[0]["s"] - st, 2) if ww else None,
        })
    json.dump(summary, open(os.path.join(a.out_dir, "audio_summary.json"), "w"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))  # numpy scalars
    print("summary written", flush=True)


if __name__ == "__main__":
    main()
