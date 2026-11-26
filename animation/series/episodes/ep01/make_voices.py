"""Генерация реплик серии закреплёнными голосами семьи (кэш: удачные реплики повторно не генерируются).
python make_voices.py VOICE_DIR [id ...] — можно перегенерировать отдельные реплики, удалив их mp3 из VOICE_DIR."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "engine"), HERE]
from voice import tts
from script import LINES
V = json.load(open(os.path.join(HERE, "..", "..", "library", "voices", "voices.json")))
out = sys.argv[1]
only = set(sys.argv[2:])
for lid, sc, who, text, note in LINES:
    if only and lid not in only:
        continue
    v = V["voices"][who]
    m = tts(v["voice_id"], text, os.path.join(out, lid + ".mp3"), settings=V["settings"], model=V["model"],
            cost_log=os.path.join(out, "cost.jsonl"), line_id=lid)
    print(lid, who, m["character_cost"], flush=True)
