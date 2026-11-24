"""Cut the Flock pitch video to the music: every scene change lands on a bar line of the 1.5x hymn."""
import json, subprocess
BIN = "/home/marcjerome/YAHSHUA/numbers-walkthroughs/recast-rig/bin/"
BAR = 4 * 0.418            # one bar of the sped-up hymn (143.6 bpm, 4/4)
MUSIC_START = 80.6         # in music/fast.wav: start of a phrase so the song's own ending lands on the closing card
# scene, bars, offset into the raw recording, narration lead-in (s), app page (crop 1536x864)
SCENES = [("s1", 3, 0.3, 0.9, False), ("s2", 5, 0.3, 0.6, False), ("s3", 2, 0.4, 0.5, False),
          ("s4", 7, 2.3, 0.4, True), ("s5", 5, 0.8, 0.6, True), ("s6", 7, 0.5, 0.2, True),
          ("s7", 3, 0.6, 0.3, True), ("s8", 5, 0.4, 0.9, False)]
narr = dict(json.load(open("narration.json")))
dur = lambda f: float(subprocess.run([BIN + "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout)

inputs, vf, af, srt, t = [], [], [], [], 0.0
for i, (name, bars, off, lead, app) in enumerate(SCENES):
    d = bars * BAR
    inputs += ["-i", f"raw/{name}.webm"]
    crop = "crop=1536:864:0:0," if app else ""
    vf.append(f"[{2*i}:v]trim={off}:{off + d},setpts=PTS-STARTPTS,{crop}scale=1920:1080,fps=30,setsar=1[v{i}]")
    a = dur(f"audio/{name}.mp3"); assert lead + a <= d + 0.05, (name, lead + a, d)
    inputs += ["-i", f"audio/{name}.mp3"]
    ms = int((t + lead) * 1000)
    af.append(f"[{len(inputs)//2 - 1}:a]adelay={ms}|{ms}[n{i}]")
    srt.append((t + lead, t + lead + a, narr[name]))
    t += d
total = t
n = len(SCENES)
inputs += ["-i", "music/fast.wav"]; mi = len(inputs) // 2 - 1
fc = ";".join(vf) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,fade=in:d=0.6,fade=out:st={total-1.2}:d=1.2[v]"
fc += ";" + ";".join(af) + ";" + "".join(f"[n{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{total},asplit[voice][key]"
fc += (f";[{mi}:a]atrim={MUSIC_START}:{MUSIC_START + total},asetpts=PTS-STARTPTS,volume=0.55,"
       f"afade=in:d=1.5,afade=out:st={total-2.5}:d=2.5[mus]"
       ";[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[duck]"
       ";[voice][duck]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=7[a]")
subprocess.run([BIN + "ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "out/flock-pitch-60s.mp4"], check=True)
ts = lambda s: f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d},{int(s%1*1000):03d}"
open("out/flock-pitch-60s.srt", "w").write("".join(f"{k+1}\n{ts(a)} --> {ts(b)}\n{txt}\n\n" for k, (a, b, txt) in enumerate(srt)))
print(f"total {total:.2f}s; music {MUSIC_START}-{MUSIC_START+total:.1f} of fast.wav")
