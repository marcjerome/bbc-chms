"""Narration for the v3 pitch videos (Brian, ElevenLabs) with word timings for captions."""
import base64, json, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = dict(l.strip().split("=", 1) for l in open(os.path.join(HERE, "..", ".env")) if "=" in l and not l.startswith("#"))["ELEVENLABS_API_KEY"]
VOICE = "nPczCjzI2devNBz1zQrb"  # Brian, same voice as v1/v2
STYLE = {"calm": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.15, "speed": 0.95},
         "blend": {"stability": 0.48, "similarity_boost": 0.8, "style": 0.32, "speed": 1.04},
         "hype": {"stability": 0.38, "similarity_boost": 0.8, "style": 0.45, "speed": 1.08}}
lines = json.load(open(os.path.join(HERE, "narration.json")))
words = {}
for version, items in lines.items():
    if len(sys.argv) > 1 and version not in sys.argv[1:]: continue
    for i, (key, text) in enumerate(items):
        if os.environ.get("ONLY") and key not in os.environ["ONLY"].split(","):
            continue
        body = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": STYLE[version],
                "previous_text": items[i - 1][1] if i else None, "next_text": items[i + 1][1] if i + 1 < len(items) else None}
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
                                     data=json.dumps(body).encode(), headers={"xi-api-key": KEY, "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=120))
        open(os.path.join(HERE, "audio", f"{version}-{key}.mp3"), "wb").write(base64.b64decode(r["audio_base64"]))
        al = r["alignment"]; ws, cur = [], None
        for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
            if ch.isspace():
                if cur: ws.append(cur); cur = None
            elif cur: cur = [cur[0] + ch, cur[1], b]
            else: cur = [ch, a, b]
        if cur: ws.append(cur)
        words[f"{version}-{key}"] = [[w, round(a, 3), round(b, 3)] for w, a, b in ws]
        print(version, key, f"{ws[-1][2]:.2f}s", text)
path = os.path.join(HERE, "audio", "words.json")
old = json.load(open(path)) if os.path.exists(path) else {}
old.update(words); json.dump(old, open(path, "w"))
