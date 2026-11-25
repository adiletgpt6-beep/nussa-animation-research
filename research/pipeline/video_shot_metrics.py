#!/usr/bin/env python3
"""Per-shot technical metrics for a locally available video (VID-001 and later).

Usage:
  video_shot_metrics.py VIDEO SEGMENTS_JSON OUT_CSV [--analysis-width 320]

SEGMENTS_JSON: [{"id": "E01", "title": "...", "start": 13.194, "end": 356.671}, ...]
Only shots inside the given segments are measured (intros/credits are skipped).

Per shot it measures (frames decoded at the source frame rate, downscaled):
  * start/end/length (s) from PySceneDetect ContentDetector;
  * motion: mean absolute luma difference between consecutive frames;
  * held_frame_ratio: share of consecutive frame pairs that are (almost) identical
    -> distinguishes animation "on ones" from "on twos"/holds. Compression noise is
       tolerated with a small threshold; treat as an estimate;
  * camera: median global translation (px/s at analysis width) and zoom rate
    (relative scale change per second) from Farneback optical flow between frames
    5 apart; a shot is flagged as camera_move if translation or zoom exceed thresholds.
Nothing is written except OUT_CSV. Frames are never saved.
"""
import argparse, csv, json, math
import numpy as np
import cv2
from scenedetect import detect, ContentDetector


def flow_stats(a, b):
    f = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    h, w = a.shape
    dx, dy = float(np.median(f[..., 0])), float(np.median(f[..., 1]))
    ys, xs = np.mgrid[0:h, 0:w]
    rx, ry = xs - w / 2, ys - h / 2
    r2 = rx * rx + ry * ry + 1e-6
    # radial component of residual flow ~ zoom
    radial = ((f[..., 0] - dx) * rx + (f[..., 1] - dy) * ry) / r2
    return dx, dy, float(np.median(radial))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("segments"); ap.add_argument("out")
    ap.add_argument("--analysis-width", type=int, default=320)
    a = ap.parse_args()
    segs = json.load(open(a.segments))
    print("detecting shots...", flush=True)
    scenes = detect(a.video, ContentDetector(threshold=27.0, min_scene_len=5))
    shots = [(s.seconds, e.seconds) for s, e in scenes]
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    W = a.analysis_width
    rows = []
    for seg in segs:
        for (s, e) in shots:
            if s < seg["start"] - 0.05 or e > seg["end"] + 0.5:
                continue
            n0, n1 = int(round(s * fps)), int(round(e * fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, n0)
            frames = []
            for _ in range(n1 - n0):
                ok, fr = cap.read()
                if not ok:
                    break
                g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
                frames.append(cv2.resize(g, (W, int(W * 9 / 16)), interpolation=cv2.INTER_AREA))
            if len(frames) < 3:
                continue
            diffs = [float(np.mean(cv2.absdiff(x, y))) for x, y in zip(frames, frames[1:])]
            held = sum(d < 0.6 for d in diffs) / len(diffs)
            tx, zm = [], []
            step = 5
            for i in range(0, len(frames) - step, step):
                dx, dy, z = flow_stats(frames[i], frames[i + step])
                tx.append(math.hypot(dx, dy) * fps / step)
                zm.append(z * fps / step)
            t_med = float(np.median(tx)) if tx else 0.0
            z_med = float(np.median(zm)) if zm else 0.0
            rows.append({
                "segment": seg["id"], "title": seg["title"],
                "shot_start_s": round(s, 3), "shot_end_s": round(e, 3), "len_s": round(e - s, 3),
                "seg_rel_start_s": round(s - seg["start"], 2),
                "motion": round(float(np.mean(diffs)), 3),
                "held_frame_ratio": round(held, 3),
                "pan_px_per_s": round(t_med, 2), "zoom_per_s": round(z_med, 4),
                "camera_move": int(t_med > 4 or abs(z_med) > 0.01),
            })
        print(seg["id"], sum(r["segment"] == seg["id"] for r in rows), "shots", flush=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
