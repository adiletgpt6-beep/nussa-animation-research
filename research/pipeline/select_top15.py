#!/usr/bin/env python3
"""Select the TOP_N (default 15) most-viewed unique full episodes from research/catalog.csv.

Rules (from the research brief):
  * only the channel's /videos tab (Shorts and live streams excluded);
  * duration 120..900 s  (shorter = shorts/teasers/clips, longer = compilations);
  * titles matching trailer / teaser / compilation / song / ad / BTS keywords excluded;
  * re-uploads and language dubs collapsed by normalised title (highest views kept).
Every exclusion is written with its reason to research/data/top15_selection_log.csv so
the selection can be audited and corrected by a human (override file supported).
"""
import csv, re, pathlib, unicodedata, json

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXCLUDE = {
    "trailer": r"\btrailer\b|\bteaser\b|\bcuplikan\b|\bsneak ?peek\b|\bofficial poster\b",
    "compilation": r"kompilasi|compilation|\bfull episodes?\b|\b\d+\s*(jam|hour|menit|minutes?)\b|marathon|spesial \d+ episode|\bkumpulan\b",
    "song/music": r"\blagu\b|\bsong\b|music video|\bmv\b|\blyric|\bnasyid\b|\bsing ?along\b|\bkaraoke\b",
    "promo/ad": r"\biklan\b|\bpromo\b|\bsponsor|\bgiveaway\b|\bmerch|\bpre-?order\b|\btiket\b|\bnow showing\b|\bdi bioskop\b",
    "making-of/other": r"behind the scenes|\bbts\b|making of|\bvlog\b|\bq&a\b|\blive\b|\bpodcast\b|\bunboxing\b|\breaction\b",
}
TOP_N = 15  # study scope reduced from 30 to 15 by the project owner (2026-11-25)
OVERRIDES = ROOT / "research/data/top15_overrides.json"  # {"exclude": {id: reason}, "include": [id]}


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").lower()
    t = re.sub(r"\(.*?\)|\[.*?\]|\|.*$", " ", t)            # drop bracketed tags and "| suffix"
    t = re.sub(r"\b(nussa|rarra|official|eps?\.?|episode|english|eng|sub|subtitle|malay|indonesia|hd|new|baru)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def main():
    rows = list(csv.DictReader(open(ROOT / "research/catalog.csv", encoding="utf-8")))
    ov = json.load(open(OVERRIDES)) if OVERRIDES.exists() else {"exclude": {}, "include": []}
    log, keep, seen = [], [], {}
    for r in sorted(rows, key=lambda r: -int(r["view_count"] or 0)):
        reason = None
        d = float(r["duration_s"] or 0)
        if r["tab"] != "videos":
            reason = f"tab={r['tab']}"
        elif r["video_id"] in ov["exclude"]:
            reason = "manual: " + ov["exclude"][r["video_id"]]
        elif r["video_id"] not in ov["include"]:
            if d < 120:
                reason = f"too short ({d:.0f}s)"
            elif d > 900:
                reason = f"too long ({d:.0f}s) - likely compilation"
            else:
                for k, pat in EXCLUDE.items():
                    if re.search(pat, (r["title"] or "").lower()):
                        reason = f"title:{k}"; break
        if not reason:
            key = norm(r["title"])
            if key in seen:
                reason = f"duplicate of {seen[key]}"
            else:
                seen[key] = r["video_id"]
        log.append({**r, "excluded_reason": reason or ""})
        if not reason:
            keep.append(r)
    with open(ROOT / "research/data/top15_selection_log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0].keys())); w.writeheader(); w.writerows(log)
    top = keep[:TOP_N]
    with open(ROOT / "research/top15.csv", "w", newline="") as f:
        fields = ["ns_id", "rank", "video_id", "title", "url", "duration_s", "view_count", "upload_date", "collected_at_utc", "analysis_status"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for i, r in enumerate(top, 1):
            w.writerow({"ns_id": f"NS-{i:03d}", "rank": i, **{k: r[k] for k in fields[2:-1]}, "analysis_status": "pending"})
    print(f"catalog={len(rows)} eligible={len(keep)} selected={len(top)}")


if __name__ == "__main__":
    main()
