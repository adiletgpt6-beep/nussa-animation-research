"""Генерация всех реплик серии 1 закреплёнными голосами (кэш: повторно не генерирует)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "engine"), HERE]
from voice import tts
from script import LINES
V = json.load(open(os.path.join(HERE, "..", "..", "library", "voices", "voices_v1_roof.json")))
out = sys.argv[1]
for lid, sc, who, text, note in LINES:
    v = V["voices"][who]
    m = tts(v["voice_id"], text, os.path.join(out, lid + ".mp3"), settings=v["settings"], model=V["model"],
            cost_log=os.path.join(out, "cost.jsonl"), line_id=lid)
    print(lid, who, m["character_cost"], flush=True)
