#!/usr/bin/env python3
"""Stage 2: measured analysis of one episode.

Usage:
  analyze_episode.py --ns NS-001 --video-id XXXXXXXXXXX --out research/data/episodes \
      [--review-dir /tmp/review] [--local-video file.mp4] [--local-subs file.vtt] [--asr]

What it produces
  <out>/<NS>.metrics.json          PUBLIC: numbers only (shots, colour, motion, loudness,
                                   speech rate, pitch), no frames, no dialogue text.
  <review-dir>/<NS>/               LOCAL ONLY (never committed, not even encrypted):
                                   subtitles/ASR transcript + frame contact sheets +
                                   motion strips used for the human review.
Media files are downloaded only to a temporary work dir and deleted; they are never
committed. Every metric records how it was obtained so reports can state what was
actually measured.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, glob, math
import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

YTDLP = ["yt-dlp", "--no-warnings", "--js-runtimes", "node"]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---------------------------------------------------------------- acquisition
def fetch_metadata(vid):
    r = run(YTDLP + ["-J", "--skip-download", f"https://www.youtube.com/watch?v={vid}"])
    if r.returncode != 0:
        return None, r.stderr[-800:]
    d = json.loads(r.stdout)
    keep = ["id", "title", "duration", "view_count", "like_count", "comment_count", "upload_date",
            "availability", "categories", "tags", "chapters", "channel", "channel_id", "language",
            "age_limit", "width", "height", "fps"]
    m = {k: d.get(k) for k in keep}
    m["description_head"] = (d.get("description") or "")[:600]
    m["subtitle_langs"] = sorted((d.get("subtitles") or {}).keys())
    m["auto_caption_langs_sample"] = [l for l in sorted((d.get("automatic_captions") or {}).keys())
                                      if l.split("-")[0] in ("id", "en", "ms", "ru", "ar")]
    return m, None


def fetch_subs(vid, work):
    r = run(YTDLP + ["--skip-download", "--write-subs", "--write-auto-subs",
                     "--sub-langs", "id,en,ms,ru,id-orig,en-orig", "--sub-format", "vtt",
                     "-o", os.path.join(work, "sub.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"])
    return sorted(glob.glob(os.path.join(work, "sub.*.vtt"))), (None if r.returncode == 0 else r.stderr[-500:])


def fetch_video(vid, work):
    out = os.path.join(work, "video.%(ext)s")
    r = run(YTDLP + ["-f", "bv*[height<=480]+ba/b[height<=480]/b", "--merge-output-format", "mp4",
                     "-o", out, f"https://www.youtube.com/watch?v={vid}"])
    files = glob.glob(os.path.join(work, "video.*"))
    return (files[0] if files else None), (None if files else r.stderr[-800:])


# ---------------------------------------------------------------- subtitles
TS = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)\s+-->\s+(\d+):(\d+):(\d+)[.,](\d+)")


def parse_vtt(path):
    cues, cur = [], None
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        m = TS.search(line)
        if m:
            g = list(map(int, m.groups()))
            cur = {"start": g[0]*3600+g[1]*60+g[2]+g[3]/1000, "end": g[4]*3600+g[5]*60+g[6]+g[7]/1000, "text": ""}
            cues.append(cur)
        elif line and cur is not None and not line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            t = re.sub(r"<[^>]+>", "", line)
            if t and t not in cur["text"]:
                cur["text"] = (cur["text"] + " " + t).strip()
    # auto-captions repeat rolling lines: drop cues whose text is contained in the next one
    out = []
    for c in cues:
        if not c["text"]:
            continue
        if out and (c["text"].startswith(out[-1]["text"]) and c["start"] - out[-1]["start"] < 4):
            out[-1] = {**out[-1], "end": c["end"], "text": c["text"]}
        else:
            out.append(c)
    return out


def speech_stats(cues, duration):
    if not cues:
        return None
    words = sum(len(c["text"].split()) for c in cues)
    speech_t = sum(max(0, c["end"] - c["start"]) for c in cues)
    gaps = [b["start"] - a["end"] for a, b in zip(cues, cues[1:])]
    def words_until(t):
        return sum(len(c["text"].split()) for c in cues if c["start"] < t)
    return {
        "cue_count": len(cues), "word_count": words,
        "first_speech_s": round(cues[0]["start"], 2),
        "words_first_5s": words_until(5), "words_first_10s": words_until(10), "words_first_30s": words_until(30),
        "speech_coverage_pct": round(100 * speech_t / duration, 1) if duration else None,
        "words_per_min_overall": round(60 * words / duration, 1) if duration else None,
        "words_per_min_while_speaking": round(60 * words / speech_t, 1) if speech_t else None,
        "median_gap_between_cues_s": round(float(np.median(gaps)), 2) if gaps else None,
        "longest_gap_s": round(max(gaps), 2) if gaps else None,
        "gaps_over_2s": sum(g > 2 for g in gaps),
        "questions_count": sum(c["text"].count("?") for c in cues),
        "exclamations_count": sum(c["text"].count("!") for c in cues),
    }


# ---------------------------------------------------------------- video
def detect_shots(path):
    from scenedetect import detect, ContentDetector
    scenes = detect(path, ContentDetector(threshold=27.0, min_scene_len=6))
    return [(float(getattr(s, 'seconds', None) or s.get_seconds()), float(getattr(e, 'seconds', None) or e.get_seconds())) for s, e in scenes]


def colorfulness(img):
    b, g, r = cv2.split(img.astype("float"))
    rg, yb = np.abs(r - g), np.abs(0.5 * (r + g) - b)
    return float(np.sqrt(rg.std()**2 + yb.std()**2) + 0.3 * np.sqrt(rg.mean()**2 + yb.mean()**2))


def frame_at(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    return f if ok else None


_face = None


def face_ratio(img):
    """Largest detected face area / frame area (Haar, heuristic; stylised faces may be missed)."""
    global _face
    if _face is None:
        try:
            _face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        except AttributeError:  # OpenCV 5 dropped Haar cascades from core
            _face = False
    if _face is False:
        return -1.0
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _face.detectMultiScale(g, 1.1, 5, minSize=(24, 24))
    if len(faces) == 0:
        return 0.0
    return float(max(w * h for x, y, w, h in faces)) / (g.shape[0] * g.shape[1])


def shot_scale(fr):
    if fr < 0:
        return "n/a"
    if fr == 0:
        return "unknown/wide"
    if fr > 0.12:
        return "close-up"
    if fr > 0.04:
        return "medium-close"
    if fr > 0.012:
        return "medium"
    return "wide"


def analyze_video(path, shots, duration):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    if not shots:
        shots = [(0.0, duration)]
    shot_rows, palette_px = [], []
    for i, (s, e) in enumerate(shots):
        L = e - s
        ts = np.linspace(s + 0.05, e - 0.05, num=max(2, min(8, int(L * 2))))
        frames = [f for f in (frame_at(cap, t) for t in ts) if f is not None]
        if not frames:
            continue
        small = [cv2.resize(f, (160, 90)) for f in frames]
        hsv = [cv2.cvtColor(f, cv2.COLOR_BGR2HSV) for f in small]
        diffs = [float(np.mean(cv2.absdiff(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY))))
                 for a, b in zip(small, small[1:])]
        # global translation (camera pan/tilt) by phase correlation between first and last sample
        g0 = np.float32(cv2.cvtColor(small[0], cv2.COLOR_BGR2GRAY)); g1 = np.float32(cv2.cvtColor(small[-1], cv2.COLOR_BGR2GRAY))
        (dx, dy), resp = cv2.phaseCorrelate(g0, g1)
        mid = frames[len(frames) // 2]
        fr = face_ratio(mid)
        edges = cv2.Canny(cv2.cvtColor(cv2.resize(mid, (320, 180)), cv2.COLOR_BGR2GRAY), 80, 160)
        shot_rows.append({
            "i": i, "start": round(s, 2), "end": round(e, 2), "len": round(L, 2),
            "brightness": round(float(np.mean([h[..., 2].mean() for h in hsv])) / 255, 3),
            "saturation": round(float(np.mean([h[..., 1].mean() for h in hsv])) / 255, 3),
            "colorfulness": round(float(np.mean([colorfulness(f) for f in small])), 1),
            "motion": round(float(np.mean(diffs)) if diffs else 0.0, 2),
            "pan_px_per_s_160w": round(math.hypot(dx, dy) / max(L, 0.1), 2) if resp > 0.15 else 0.0,
            "face_ratio": round(fr, 4), "scale_guess": shot_scale(fr),
            "edge_density": round(float((edges > 0).mean()), 4),
        })
        palette_px.append(cv2.resize(mid, (32, 18)).reshape(-1, 3))
    cap.release()
    lens = np.array([r["len"] for r in shot_rows]) if shot_rows else np.array([duration])
    px = np.float32(np.concatenate(palette_px)) if palette_px else None
    palette = []
    if px is not None and len(px) >= 8:
        _, labels, centers = cv2.kmeans(px, 8, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0), 3, cv2.KMEANS_PP_CENTERS)
        counts = np.bincount(labels.flatten(), minlength=8)
        for c, n in sorted(zip(centers, counts), key=lambda x: -x[1]):
            b, g, r = [int(v) for v in c]
            palette.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share": round(float(n) / len(px), 3)})

    def cuts_before(t):
        return sum(1 for r in shot_rows[1:] if r["start"] < t)
    scales = {}
    for r in shot_rows:
        scales[r["scale_guess"]] = scales.get(r["scale_guess"], 0) + 1
    first30 = [r for r in shot_rows if r["start"] < 30]
    rest = [r for r in shot_rows if r["start"] >= 30]
    return {
        "fps_source": round(fps, 2),
        "shot_count": len(shot_rows),
        "asl_s": round(float(lens.mean()), 2), "median_shot_s": round(float(np.median(lens)), 2),
        "shortest_shot_s": round(float(lens.min()), 2), "longest_shot_s": round(float(lens.max()), 2),
        "shots_per_min": round(60 * len(shot_rows) / duration, 1) if duration else None,
        "cuts_first_5s": cuts_before(5), "cuts_first_10s": cuts_before(10), "cuts_first_30s": cuts_before(30),
        "motion_first30_vs_rest": [round(float(np.mean([r["motion"] for r in first30])), 2) if first30 else None,
                                   round(float(np.mean([r["motion"] for r in rest])), 2) if rest else None],
        "mean_brightness": round(float(np.mean([r["brightness"] for r in shot_rows])), 3) if shot_rows else None,
        "mean_saturation": round(float(np.mean([r["saturation"] for r in shot_rows])), 3) if shot_rows else None,
        "shots_with_camera_move": sum(1 for r in shot_rows if r["pan_px_per_s_160w"] > 2),
        "shot_scale_guess_counts": scales,
        "palette": palette,
        "shots": shot_rows,
    }


# ---------------------------------------------------------------- audio
def analyze_audio(path, work, cues):
    wav = os.path.join(work, "a.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", wav])
    if not os.path.exists(wav):
        return None
    r = run(["ffmpeg", "-nostats", "-i", path, "-filter_complex", "ebur128=peak=true", "-f", "null", "-"])
    txt = r.stderr
    def grab(pat):
        m = re.findall(pat, txt)
        return float(m[-1]) if m else None
    loud = {"integrated_lufs": grab(r"I:\s+(-?[\d.]+) LUFS"), "lra_lu": grab(r"LRA:\s+([\d.]+) LU"),
            "true_peak_dbfs": grab(r"Peak:\s+(-?[\d.]+) dBFS")}
    s = run(["ffmpeg", "-i", wav, "-af", "silencedetect=noise=-38dB:d=0.35", "-f", "null", "-"]).stderr
    sil = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", s)]
    out = {"loudness": loud, "silences_over_0_35s": len(sil),
           "silence_total_s": round(sum(sil), 1), "longest_silence_s": round(max(sil), 2) if sil else 0}
    try:
        import librosa
        y, sr = librosa.load(wav, sr=16000)
        rms = librosa.feature.rms(y=y, frame_length=16000, hop_length=16000)[0]
        db = 20 * np.log10(rms + 1e-6)
        out["rms_db_per_second_p10_p50_p90"] = [round(float(np.percentile(db, p)), 1) for p in (10, 50, 90)]
        # pitch of speech segments (from subtitle timing when available)
        segs = [(c["start"], c["end"]) for c in (cues or [])][:120] or [(0, min(len(y) / sr, 300))]
        f0s = []
        for a, b in segs:
            seg = y[int(a * sr):int(b * sr)]
            if len(seg) < sr * 0.3:
                continue
            f0, vflag, _ = librosa.pyin(seg, fmin=80, fmax=600, sr=sr, frame_length=1024)
            v = f0[vflag & ~np.isnan(f0)]
            if len(v):
                f0s.append(float(np.median(v)))
        if f0s:
            f0s = np.array(f0s)
            out["speech_f0_median_hz_per_line"] = {
                "p10": round(float(np.percentile(f0s, 10))), "p50": round(float(np.median(f0s))),
                "p90": round(float(np.percentile(f0s, 90))),
                "share_lines_over_250hz": round(float((f0s > 250).mean()), 2),
                "share_lines_under_165hz": round(float((f0s < 165).mean()), 2), "lines_measured": int(len(f0s))}
    except Exception as e:  # librosa optional
        out["librosa_error"] = str(e)[:200]
    return out, wav


def run_asr(wav):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None, "faster-whisper not installed"
    model = WhisperModel(os.environ.get("ASR_MODEL", "small"), device="cpu", compute_type="int8")
    segs, info = model.transcribe(wav, vad_filter=True, beam_size=1)
    cues = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    return {"language": info.language, "language_probability": round(info.language_probability, 2), "cues": cues}, None


# ---------------------------------------------------------------- review pack
def contact_sheet(frames, cols, out, tile=(256, 144), label_ts=None):
    rows = math.ceil(len(frames) / cols)
    sheet = np.zeros((rows * tile[1], cols * tile[0], 3), np.uint8)
    for k, f in enumerate(frames):
        t = cv2.resize(f, tile)
        if label_ts:
            cv2.putText(t, label_ts[k], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        r, c = divmod(k, cols)
        sheet[r*tile[1]:(r+1)*tile[1], c*tile[0]:(c+1)*tile[0]] = t
    cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 72])


def review_pack(path, vstats, cues, pdir):
    cap = cv2.VideoCapture(path)
    os.makedirs(pdir, exist_ok=True)
    ts = [float(t) for t in range(0, 30)]
    fr = [frame_at(cap, t) for t in ts]
    contact_sheet([f for f in fr if f is not None], 6, os.path.join(pdir, "hook_first30s_1fps.jpg"),
                  label_ts=[f"{t:.0f}s" for t, f in zip(ts, fr) if f is not None])
    shots = vstats["shots"]
    mids = [((r["start"] + r["end"]) / 2, r) for r in shots]
    for page in range(0, len(mids), 30):
        chunk = mids[page:page + 30]
        fr = [frame_at(cap, t) for t, _ in chunk]
        contact_sheet([f for f in fr if f is not None], 6, os.path.join(pdir, f"shots_{page//30+1:02d}.jpg"),
                      label_ts=[f"#{r['i']} {r['start']:.1f}s {r['len']:.1f}s" for (t, r), f in zip(chunk, fr) if f is not None])
    # motion strips: 12 consecutive frames at ~12 fps
    picks = {}
    if shots:
        picks["max_motion"] = max(shots, key=lambda r: r["motion"])
        picks["longest"] = max(shots, key=lambda r: r["len"])
        if cues:
            c = max(cues, key=lambda c: c["end"] - c["start"])
            picks["dialogue"] = {"start": c["start"], "end": c["end"], "len": c["end"] - c["start"]}
    for name, r in picks.items():
        t0 = r["start"] + max(0.0, (r["len"] - 1.0) / 2)
        fr = [frame_at(cap, t0 + k / 12) for k in range(12)]
        contact_sheet([f for f in fr if f is not None], 4, os.path.join(pdir, f"strip_{name}.jpg"), tile=(384, 216),
                      label_ts=[f"{t0 + k/12:.2f}s" for k, f in enumerate(fr) if f is not None])
    cap.release()


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", required=True); ap.add_argument("--video-id", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--review-dir", help="local-only folder for transcript+frames (never commit)")
    ap.add_argument("--local-video"); ap.add_argument("--local-subs"); ap.add_argument("--asr", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="ep_")
    res = {"ns_id": a.ns, "video_id": a.video_id, "status": {}, "errors": {}}
    try:
        if a.local_video:
            meta, err = {"id": a.video_id, "duration": None}, None
        else:
            meta, err = fetch_metadata(a.video_id)
        res["status"]["metadata_verified"] = meta is not None and not a.local_video
        if err: res["errors"]["metadata"] = err
        res["metadata"] = meta
        subs = [a.local_subs] if a.local_subs else fetch_subs(a.video_id, work)[0]
        pref = sorted(subs, key=lambda p: (0 if re.search(r"\.id\.vtt$", p) else 1 if ".id" in p else 2 if ".en" in p else 3))
        cues = parse_vtt(pref[0]) if pref else []
        res["status"]["subtitles"] = [os.path.basename(p) for p in subs]
        video, verr = (a.local_video, None) if a.local_video else fetch_video(a.video_id, work)
        res["status"]["video_downloaded"] = bool(video)
        if verr: res["errors"]["video"] = verr
        duration = (meta or {}).get("duration")
        if video:
            p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video])
            duration = float(p.stdout.strip() or duration or 0)
        res["duration_s"] = duration
        asr = None
        if video:
            shots = detect_shots(video)
            v = analyze_video(video, shots, duration)
            res["video"] = v; res["status"]["frames_measured"] = True; res["status"]["motion_measured"] = True
            aud = analyze_audio(video, work, cues)
            if aud:
                res["audio"], wav = aud; res["status"]["audio_measured"] = True
                if a.asr and not any(re.search(r"\.(id|en|ms)\.vtt$", p) for p in subs):
                    asr, aerr = run_asr(wav)
                    res["status"]["asr"] = bool(asr)
                    if aerr: res["errors"]["asr"] = aerr
                    if asr and not cues:
                        cues = asr["cues"]
        res["speech"] = speech_stats(cues, duration) if duration else None
        res["status"]["speech_source"] = ("subtitles:" + os.path.basename(pref[0])) if pref else ("asr" if asr else None)
        if a.review_dir:
            # LOCAL ONLY: transcript + contact sheets for human review. Never commit this folder.
            pdir = os.path.join(a.review_dir, a.ns)
            os.makedirs(pdir, exist_ok=True)
            json.dump({"cues": cues, "asr": asr, "subtitle_files": res["status"]["subtitles"]},
                      open(os.path.join(pdir, "transcript.json"), "w"), ensure_ascii=False, indent=1)
            for p in subs:
                shutil.copy(p, pdir)
            if video:
                review_pack(video, res["video"], cues, pdir)
            res["status"]["review_pack_local"] = True
    finally:
        shutil.rmtree(work, ignore_errors=True)
    json.dump(res, open(os.path.join(a.out, f"{a.ns}.metrics.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("ns_id", "video_id", "status", "errors")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
