#!/usr/bin/env python3
"""Build research/data/episodes_summary.csv from research/data/episodes/NS-0XX.json.

Only fields actually present in the per-episode JSON are used; missing values stay empty.
"""
import csv, glob, json, pathlib, statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[2]
rows = []
for p in sorted(glob.glob(str(ROOT / "research/data/episodes/NS-0*.json"))):
    d = json.load(open(p))
    dur = d.get("duration_s")
    words = d.get("manual_words_excl_labels") or d.get("manual_words_excl_labels_approx") \
        or d.get("manual_words_excl_labels_dialogue_only") or d.get("word_count")
    shot = d.get("avg_shot_len_story_s_approx") or d.get("avg_shot_len_story_s_upper_bound")
    rows.append({
        "ns_id": d["ns_id"], "video_id": d["video_id"], "view_count": d.get("view_count"),
        "upload_year": str(d.get("upload_date", ""))[:4], "duration_s": dur,
        "first_story_line_s": d.get("manual_first_line_s") or d.get("first_speech_s"),
        "story_start_s_approx": d.get("story_start_s_approx"),
        "words_manual_or_asr": words,
        "wpm_full_duration": round(60 * words / dur, 1) if words and dur else None,
        "wpm_active_speech_asr": d.get("wpm_over_active_speech"),
        "pauses_ge_3s": d.get("pauses_ge_3s"),
        "question_marks": d.get("manual_question_marks"), "exclamation_marks": d.get("manual_exclamation_marks"),
        "avg_shot_len_s": shot,
        "avg_shot_len_kind": "approx" if d.get("avg_shot_len_story_s_approx") else ("upper_bound" if shot else "not_countable"),
        "storyboard_px": d.get("storyboard_frame_px"), "storyboard_step_s": d.get("storyboard_interval_s"),
        "sponsor": bool(d.get("sponsor")), "special": bool(d.get("flags")),
        "depicts_shaitan": d.get("depicts_shaitan"),
        "tag_scene_after_moral": d.get("tag_scene_after_moral"),
        "analysis_completeness_pct": d.get("analysis_completeness_pct"),
    })
out = ROOT / "research/data/episodes_summary.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
reg = [r for r in rows if not r["special"]]
def med(k, rs):
    v = [r[k] for r in rs if isinstance(r[k], (int, float))]
    return (round(st.median(v), 1), len(v)) if v else None
print(f"episodes={len(rows)} regular={len(reg)}")
for k in ("duration_s", "story_start_s_approx", "first_story_line_s", "wpm_full_duration", "wpm_active_speech_asr", "avg_shot_len_s", "analysis_completeness_pct"):
    print(k, "median(all)=", med(k, rows), "median(regular)=", med(k, reg))
