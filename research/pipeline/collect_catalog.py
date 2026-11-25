#!/usr/bin/env python3
"""Stage 1: build the channel catalog with yt-dlp (metadata only, no media).

Runs on GitHub Actions (the research container has no YouTube access).
Writes research/catalog.csv and research/data/catalog_raw.jsonl.
"""
import csv, json, subprocess, sys, datetime, pathlib

CHANNEL = "https://www.youtube.com/@NussaOfficialSeries"
TABS = ["videos", "shorts", "streams"]
ROOT = pathlib.Path(__file__).resolve().parents[2]
YTDLP = ["yt-dlp", "--ignore-errors", "--no-warnings", "--js-runtimes", "node"]


def flat(tab):
    cmd = YTDLP + ["--flat-playlist", "-J", f"{CHANNEL}/{tab}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 and not r.stdout.strip():
        print(f"[{tab}] FAILED: {r.stderr[-2000:]}", file=sys.stderr)
        return None, r.stderr[-500:]
    data = json.loads(r.stdout)
    return data, None


def main():
    collected = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, raw, info = [], [], {"collected_at_utc": collected, "channel": CHANNEL, "tabs": {}}
    for tab in TABS:
        data, err = flat(tab)
        if data is None:
            info["tabs"][tab] = {"status": "error", "error": err}
            continue
        entries = data.get("entries") or []
        info["tabs"][tab] = {"status": "ok", "count": len(entries)}
        if tab == "videos":
            info["channel_title"] = data.get("channel") or data.get("title")
            info["channel_id"] = data.get("channel_id")
            info["channel_follower_count"] = data.get("channel_follower_count")
        for pos, e in enumerate(entries, 1):
            raw.append({"tab": tab, **e})
            vid = e.get("id")
            rows.append({
                "video_id": vid,
                "title": e.get("title"),
                "url": f"https://www.youtube.com/watch?v={vid}" if tab != "shorts" else f"https://www.youtube.com/shorts/{vid}",
                "tab": tab,
                "tab_position": pos,
                "duration_s": e.get("duration"),
                "view_count": e.get("view_count"),
                "upload_date": e.get("upload_date") or "",
                "timestamp": e.get("timestamp") or "",
                "availability": e.get("availability") or "",
                "live_status": e.get("live_status") or "",
                "collected_at_utc": collected,
            })
    (ROOT / "research/data").mkdir(parents=True, exist_ok=True)
    with open(ROOT / "research/data/catalog_raw.jsonl", "w") as f:
        for r in raw:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(ROOT / "research/catalog.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["video_id"])
        w.writeheader(); w.writerows(rows)
    json.dump(info, open(ROOT / "research/data/catalog_info.json", "w"), ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    if not rows:
        sys.exit(1)


if __name__ == "__main__":
    main()
