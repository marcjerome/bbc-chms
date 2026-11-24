"""Burn short, readable captions into the pitch video (one file to send)."""
import json, re, subprocess, sys
D = sys.argv[1] if len(sys.argv) > 1 else "out"  # folder holding flock-pitch-60s.mp4/.srt
CARDS = D == "out"  # v2 shows "No lines./No logbooks." as big text
BIN = "/home/marcjerome/YAHSHUA/numbers-walkthroughs/recast-rig/bin/"
# Scenes whose lower-third verse box sits bottom-left: lift captions above it.
LIFT = {2: 215, 7: 215}
def secs(s):
    h, m, rest = s.split(":"); sec, ms = rest.split(","); return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
def ass_t(t):
    return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
WORDS = json.load(open("audio/words.json"))
cues = []
for block in open(f"{D}/flock-pitch-60s.srt").read().strip().split("\n\n"):
    idx, times, _ = block.split("\n", 2)
    a = secs(times.split(" --> ")[0]); words = WORDS[f"s{idx}"]
    groups, cur = [], []
    for w in words:  # break at punctuation, or before a line gets too long
        if cur and (len(" ".join(x[0] for x in cur + [w])) > 52 or cur[-1][0][-1] in ".!?" or (cur[-1][0][-1] == "," and len(" ".join(x[0] for x in cur)) > 22)):
            groups.append(cur); cur = []
        cur.append(w)
    groups.append(cur)
    for k, g in enumerate(groups):
        start = a + g[0][1] - 0.05
        end = a + (groups[k + 1][0][1] - 0.08 if k + 1 < len(groups) and groups[k + 1][0][1] - g[-1][2] < 0.9 else g[-1][2] + 0.35)
        txt = " ".join(x[0] for x in g).rstrip(",")
        if CARDS and txt in ("No lines.", "No logbooks."): continue  # already on screen as the big moving text
        cues.append((start, end, txt, LIFT.get(int(idx), 70)))
head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Liberation Sans,46,&H00F5F9FB,&H00F5F9FB,&H2A321604,&H2A321604,1,0,0,0,100,100,0.5,0,3,14,0,2,200,200,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = [f"Dialogue: 0,{ass_t(a)},{ass_t(b - 0.05)},Cap,,0,0,{mv},,{txt}" for a, b, txt, mv in cues]
open(f"{D}/captions.ass", "w").write(head + "\n".join(lines) + "\n")
subprocess.run([BIN + "ffmpeg", "-v", "error", "-y", "-i", f"{D}/flock-pitch-60s.mp4", "-vf", f"ass={D}/captions.ass",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy",
                "-movflags", "+faststart", f"{D}/flock-pitch-60s-captioned.mp4"], check=True)
print(len(cues), "captions burned")
