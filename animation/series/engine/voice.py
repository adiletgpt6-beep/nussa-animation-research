"""Озвучка ElevenLabs (eleven_v3) с таймингами символов. Кэш: удачные реплики не генерируются повторно.
Каждый запрос пишет фактическую стоимость (заголовок `character-cost`) в журнал расходов."""
import os, json, base64, time, hashlib, subprocess
import urllib.request

API = "https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128"


def tts(voice_id, text, out_mp3, settings=None, model="eleven_v3", cost_log=None, line_id=None):
    meta_p = out_mp3 + ".json"
    if os.path.exists(out_mp3) and os.path.exists(meta_p):
        return json.load(open(meta_p))  # кэш — без повторной генерации
    body = {"text": text, "model_id": model, "language_code": "ru"}
    if settings:
        body["voice_settings"] = settings
    req = urllib.request.Request(API.format(vid=voice_id), data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                cost = r.headers.get("character-cost")
                rid = r.headers.get("request-id")
                d = json.loads(r.read())
            break
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(3)
    os.makedirs(os.path.dirname(out_mp3), exist_ok=True)
    open(out_mp3, "wb").write(base64.b64decode(d["audio_base64"]))
    meta = {"voice_id": voice_id, "model": model, "text": text, "settings": settings, "alignment": d.get("normalized_alignment") or d.get("alignment"),
            "character_cost": int(cost) if cost else None, "request_id": rid, "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
    json.dump(meta, open(meta_p, "w"), ensure_ascii=False)
    if cost_log:
        with open(cost_log, "a") as f:
            f.write(json.dumps({"line": line_id, "voice_id": voice_id, "chars": len(text), "character_cost": meta["character_cost"],
                                "request_id": rid, "time": meta["time"]}, ensure_ascii=False) + "\n")
    return meta


def to_wav(mp3, wav, sr=48000):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", str(sr), wav], check=True)
