"""v2 'hype' cut: clips measured in beats of the 1.5x hymn, effects and sound cues on beats."""
import json, subprocess
BIN = "/home/marcjerome/YAHSHUA/numbers-walkthroughs/recast-rig/bin/"
BEAT = 0.418; MUSIC_START = 80.6
# clip, beats, app page (crop 1536x864 from 1920 frame)
CLIPS = [("s1", 12, 0), ("s2", 20, 0), ("s3", 8, 0), ("s4a", 13, 1), ("s4b", 6, 0), ("s4c", 9, 1), ("s5", 20, 1),
         ("s6a", 7, 1), ("s6b", 5, 1), ("s6c", 7, 1), ("s6d", 9, 1), ("s7a", 4, 0), ("s7b", 8, 1), ("s8", 20, 0)]
NARR = {"s1": ("s1", 0.9), "s2": ("s2", 0.6), "s3": ("s3", 0.5), "s4": ("s4a", 0.4), "s5": ("s5", 0.6),
        "s6": ("s6a", 0.2), "s7": ("s7a", 0.3), "s8": ("s8", 0.9)}
start, t = {}, 0.0
for name, beats, _ in CLIPS: start[name] = t; t += beats * BEAT
total = t
b = lambda clip, beat: start[clip] + beat * BEAT
SFX = [("riser", start["s3"] - 1.6, 0.35), ("chime", b("s3", 2.1), 0.5), ("tick", b("s4a", 3.5), 0.6), ("tick", b("s4a", 10.1), 0.45),
       ("thump", b("s4b", 1), 0.7), ("thump", b("s4b", 3), 0.7), ("tick", b("s4c", 3.5), 0.6), ("tick", b("s6b", 0.8), 0.5),
       ("thump", b("s7a", 0), 0.7), ("tick", b("s7b", 3), 0.5), ("chime", b("s8", 9.3), 0.55)]
narr = dict(json.load(open("narration.json")))
dur = lambda f: float(subprocess.run([BIN + "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout)
inputs, fc, srt = [], [], []
def add(path):
    inputs.extend(["-i", path]); return len(inputs) // 2 - 1
for i, (name, beats, app) in enumerate(CLIPS):
    off = json.load(open(f"raw2/{name}.json"))["offset"]; d = beats * BEAT
    k = add(f"raw2/{name}.webm")
    fc.append(f"[{k}:v]trim={off:.3f}:{off + d:.3f},setpts=PTS-STARTPTS,{'crop=1536:864:0:0,' if app else ''}scale=1920:1080,fps=30,setsar=1[v{i}]")
voices = []
for i, (scene, (clip, lead)) in enumerate(NARR.items()):
    k = add(f"audio/{scene}.mp3"); ms = int((start[clip] + lead) * 1000); a = dur(f"audio/{scene}.mp3")
    fc.append(f"[{k}:a]adelay={ms}|{ms}[n{i}]"); voices.append(f"[n{i}]")
    srt.append((start[clip] + lead, start[clip] + lead + a, narr[scene]))
fx = []
for i, (s, at, vol) in enumerate(SFX):
    k = add(f"sfx/{s}.wav"); ms = int(max(at, 0) * 1000)
    fc.append(f"[{k}:a]volume={vol},adelay={ms}|{ms}[f{i}]"); fx.append(f"[f{i}]")
m = add("music/fast.wav")
n = len(CLIPS)
fc.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,fade=in:d=0.6,fade=out:st={total-1.2:.3f}:d=1.2[v]")
fc.append("".join(voices) + f"amix=inputs={len(voices)}:normalize=0,apad,atrim=0:{total:.3f},asplit[voice][key]")
fc.append("".join(fx) + f"amix=inputs={len(fx)}:normalize=0,apad,atrim=0:{total:.3f}[fx]")
fc.append(f"[{m}:a]atrim={MUSIC_START}:{MUSIC_START + total:.3f},asetpts=PTS-STARTPTS,volume=0.55,afade=in:d=1.5,afade=out:st={total-2.5:.3f}:d=2.5[mus]")
fc.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[duck]")
fc.append("[voice][duck][fx]amix=inputs=3:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=7[a]")
subprocess.run([BIN + "ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "out/flock-pitch-60s.mp4"], check=True)
ts = lambda s: f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d},{int(s%1*1000):03d}"
open("out/flock-pitch-60s.srt", "w").write("".join(f"{k+1}\n{ts(a)} --> {ts(b)}\n{txt}\n\n" for k, (a, b, txt) in enumerate(srt)))
print(f"total {total:.2f}s")
