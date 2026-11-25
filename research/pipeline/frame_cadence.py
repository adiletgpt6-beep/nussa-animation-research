#!/usr/bin/env python3
"""Frame-cadence check: finds exact/near-exact duplicate frames inside moving footage.

Usage:
  frame_cadence.py VIDEO OUT_JSON --window START:DUR [--window START:DUR ...] [--width 320]

For each window, frames are decoded at the native rate (ffmpeg, grayscale, downscaled).
A frame pair counts as "duplicate" if mean abs diff < DUP (default 0.25) while the
surrounding motion is clearly above it (>= 3x DUP on both neighbours) - i.e. a repeated
frame in the middle of movement, not a static hold. The JSON reports the gaps (in frames)
between consecutive duplicates; a dominant gap of 25 at 25 fps means one repeated frame
per second (typical of a 24 -> 25 fps conversion). Numbers only; no frames are saved.
"""
import argparse, json, subprocess
from collections import Counter
import numpy as np


def frames(video, start, dur, w):
    h = int(w * 9 / 16)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", video,
                          "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.int16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--window", action="append", required=True)
    ap.add_argument("--width", type=int, default=320); ap.add_argument("--dup", type=float, default=0.25)
    a = ap.parse_args()
    res = []
    for wdef in a.window:
        st, du = map(float, wdef.split(":"))
        f = frames(a.video, st, du, a.width)
        d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
        dups = [i for i in range(1, len(d) - 1)
                if d[i] < a.dup and d[i - 1] >= 3 * a.dup and d[i + 1] >= 3 * a.dup]
        gaps = Counter(int(b - x) for x, b in zip(dups, dups[1:]))
        res.append({"start_s": st, "dur_s": du, "frames": int(len(f)),
                    "share_pairs_moving_ge_1": round(float((d >= 1).mean()), 3),
                    "duplicates_in_motion": len(dups),
                    "gap_histogram_top": gaps.most_common(5)})
    json.dump({"method": f"mean abs luma diff at {a.width}px; dup<{a.dup}, neighbours>={3*a.dup}",
               "windows": res}, open(a.out, "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
