"""Assemble a v3 pitch cut on "Love Lifted Me": python3 assemble3.py calm|blend|hype

Every scene starts on a beat (plan-<version>.json, from plan.py); narration lines start a fixed lead after
their scene's cut; the door scene is trimmed so the kiosk's "Welcome" lands on the word "greeted".
Writes out/v3/flock-pitch-<version>.mp4 (+ .srt) and flock-pitch-<version>-captioned.mp4.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = "/home/marcjerome/YAHSHUA/numbers-walkthroughs/recast-rig/bin/"
SONG = os.path.join(HERE, "..", "music2", "love-lifted-me.mp3")
VERSION = sys.argv[1]
P = json.load(open(os.path.join(HERE, f"plan-{VERSION}.json")))
NARR = dict(json.load(open(os.path.join(HERE, "narration.json")))[VERSION])
WORDS = json.load(open(os.path.join(HERE, "audio", "words.json")))
RAW = os.path.join(HERE, f"raw-{VERSION}")
OUT = os.path.join(HERE, "..", "out", "v3"); os.makedirs(OUT, exist_ok=True)
CALM = VERSION == "calm"
BLEND = VERSION == "blend"      # calm's story and song path at 1.2x, with the hype cut's accents (softer)
SMOOTH = CALM or BLEND
APP = {"door", "modes", "dash", "visitor", "roll", "bday", "visit"}          # recorded at 1536x864: crop
XF = 0.5 if CALM else 0.35 if BLEND else 0.0                       # calm/blend: dissolves; hype: hard cuts
clips = P["clips"]; total = P["total"]; beat = P["beat"]

def wt(key, w):  # start time of word w in a narration line
    return next(a for x, a, _ in WORDS[f"{VERSION}-{key}"] if x.strip(".,!?").lower() == w)

# narration lead after each cut
lead = {c["name"]: P["lead"] for c in clips}
lead.update({"s1": 1.0 if CALM else 0.8 if BLEND else 0.45, "s3": 0.5, "lines": 0.5 if BLEND else beat, "s8": 3.3 if CALM else 2.8 if BLEND else 3.3})
start = {c["name"]: c["start"] for c in clips}
# the kiosk says "Welcome" just as the narrator says "greeted"
welcome_at = lead["door"] + wt("door", "greeted") - 0.2

inputs, fc = [], []
def add(*args):
    inputs.extend(args); return sum(1 for a in inputs if a == "-i") - 1

# ---- video
for i, c in enumerate(clips):
    meta = json.load(open(f"{RAW}/{c['name']}.json"))
    off = meta["event"] - welcome_at if c["name"] == "door" else meta["offset"]
    assert off >= 0, (c["name"], off)
    d = c["dur"] + (XF if i + 1 < len(clips) else 0)
    k = add("-i", f"{RAW}/{c['name']}.webm")
    crop = "crop=1536:864:0:0," if c["name"] in APP else ""
    fc.append(f"[{k}:v]trim={off:.3f}:{off + d:.3f},setpts=PTS-STARTPTS,{crop}scale=1920:1080,fps=30,setsar=1,format=yuv420p[v{i}]")
if XF:
    prev = "v0"
    for i in range(1, len(clips)):
        fc.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={clips[i]['start']:.3f}[x{i}]"); prev = f"x{i}"
    vlast = prev
else:
    fc.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[xc]"); vlast = "xc"
fc.append(f"[{vlast}]fade=in:d={0.8 if SMOOTH else 0.25},fade=out:st={total - 1.6:.3f}:d=1.6[v]")

# ---- narration
voices, srt = [], []
for c in clips:
    n = c["name"]; f = os.path.join(HERE, "audio", f"{VERSION}-{n}.mp3")
    at = start[n] + lead[n]; ln = WORDS[f"{VERSION}-{n}"][-1][2]
    assert at + ln <= start[n] + c["dur"] + (2.5 if n in ("dash", "visitor", "roll", "bday") else 0.05), (n, at + ln, start[n] + c["dur"])
    k = add("-i", f); ms = int(at * 1000)
    fc.append(f"[{k}:a]adelay={ms}|{ms}[n_{n}]"); voices.append(f"[n_{n}]")
    srt.append((at, at + ln, NARR[n], n))
fc.append("".join(voices) + f"amix=inputs={len(voices)}:normalize=0,apad,atrim=0:{total:.3f},asplit[voice][key]")

# ---- sound effects (on the beat / on the action)
sfx = [("chime", start["door"] + welcome_at - 0.05, 0.35 if CALM else 0.45 if BLEND else 0.5)]
if BLEND:   # accents: a lift into "Meet Flock", the two slams, the chorus arriving, the taps
    lw = WORDS["blend-lines"]; ln_at = start["lines"] + lead["lines"]
    sfx += [("riser", start["s3"] - 1.6, 0.2), ("thump", ln_at + lw[0][1], 0.5), ("thump", ln_at + lw[2][1], 0.5),
            ("thump", start["dash"], 0.3), ("tick", start["visitor"] + 0.8 * beat, 0.4), ("tick", start["visit"] + 3 * beat, 0.35)]
if not SMOOTH:
    lw = WORDS["hype-lines"]
    sfx += [("riser", start["bible"] - 1.6, 0.3), ("thump", start["lines"] + lead["lines"] + lw[0][1], 0.7),
            ("thump", start["lines"] + lead["lines"] + lw[2][1], 0.7), ("thump", start["dash"], 0.45),
            ("tick", start["visitor"] + 0.8 * beat, 0.5), ("tick", start["visit"] + 3 * beat, 0.45)]
fx = []
for i, (s, at, vol) in enumerate(sfx):
    k = add("-i", os.path.join(HERE, "..", "sfx", f"{s}.wav")); ms = int(max(at, 0) * 1000)
    fc.append(f"[{k}:a]volume={vol},adelay={ms}|{ms}[f{i}]"); fx.append(f"[f{i}]")
fc.append("".join(fx) + f"amix=inputs={len(fx)}:normalize=0,apad,atrim=0:{total:.3f}[fx]")

# ---- music bed
segs = P["segments"]
if SMOOTH:  # pass 1 -> (seamless splice, 116.1 s later in the song) -> last chorus line + ending (blend: 1.2x, pitch kept)
    (a1, b1), (a2, b2) = segs; h = 0.06
    k1 = add("-i", SONG); k2 = add("-i", SONG)
    fc.append(f"[{k1}:a]atrim={a1}:{b1 + h},asetpts=PTS-STARTPTS[m1]")
    fc.append(f"[{k2}:a]atrim={a2 - h}:{b2},asetpts=PTS-STARTPTS[m2]")
    tempo = ",rubberband=tempo=1.2:pitchq=quality" if BLEND else ""
    fc.append(f"[m1][m2]acrossfade=d={2 * h}:c1=tri:c2=tri{tempo},volume={0.55 if BLEND else 0.5},afade=in:d=0.4[mus0]")
else:     # 1.5x, pitch kept
    (a1, b1), = segs
    k1 = add("-i", SONG)
    fc.append(f"[{k1}:a]atrim={a1 - 0.03}:{b1},asetpts=PTS-STARTPTS,rubberband=tempo=1.5:pitchq=quality,volume=0.6,afade=in:d=0.08[mus0]")
fc.append(f"[mus0]apad,atrim=0:{total:.3f},afade=out:st={total - 1.2:.3f}:d=1.2[mus]")
fc.append("[mus][key]sidechaincompress=threshold=0.03:ratio=5:attack=40:release=450[duck]")
fc.append("[voice][duck][fx]amix=inputs=3:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]")

base = os.path.join(OUT, f"flock-pitch-{VERSION}")
subprocess.run([BIN + "ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", base + ".mp4"], check=True)

# ---- captions: short lines broken at punctuation, timed to the words
ts = lambda s: f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(s % 1 * 1000):03d}"
open(base + ".srt", "w").write("".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{t}\n\n" for i, (a, b, t, _) in enumerate(srt)))
cues = []
for a, _, _, n in srt:
    if n == "lines" and VERSION == "hype": continue                      # already on screen as the big moving words
    ws, groups, cur = WORDS[f"{VERSION}-{n}"], [], []
    for w in ws:
        if cur and (len(" ".join(x[0] for x in cur + [w])) > 52 or cur[-1][0][-1] in ".!?"):
            groups.append(cur); cur = []
        cur.append(w)
    groups.append(cur)
    for g in groups:
        txt = " ".join(x[0] for x in g).rstrip(",")
        if n == "lines" and txt in ("No lines.", "No logbooks."): continue
        cues.append((a + g[0][1] - 0.05, a + g[-1][2] + 0.35, txt, 215 if n in ("s2", "visit") else 70))
for i in range(len(cues) - 1):  # never overlap the next caption
    if cues[i][1] > cues[i + 1][0] - 0.05: cues[i] = (cues[i][0], cues[i + 1][0] - 0.05, *cues[i][2:])
at = lambda t: f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
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
open(base + ".ass", "w").write(head + "\n".join(f"Dialogue: 0,{at(a)},{at(b)},Cap,,0,0,{mv},,{t}" for a, b, t, mv in cues) + "\n")
subprocess.run([BIN + "ffmpeg", "-v", "error", "-y", "-i", base + ".mp4", "-vf", f"ass={base}.ass", "-c:v", "libx264",
                "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                base + "-captioned.mp4"], check=True)
print(f"{VERSION}: {total:.1f}s, {len(cues)} captions -> {base}.mp4")
