"""Edit plans for the two v3 pitch cuts of "Love Lifted Me" (piano, 72 bpm, 4/4).

Song map (original time): intro 0-18.3 (soft) | three verse+chorus passes of 58.05 s starting 18.3, 76.3, 134.5
(verse ~0-30 s into a pass, chorus ~30-50 s, peak at ~30 s, held note ~44 s, soft close ~50-58 s) | final chord
~185.2, ringing out to 196. The passes are near-identical (chroma similarity 0.99), so a cut from 59.44 in pass 1
to 175.54 in pass 3 (same spot, 116.1 s later) is seamless.

blend 1.2x  calm's story, dissolves and ending, with more drive (86 bpm, sound accents)   ~66 s
calm  1.0x  intro -> pass 1 verse + chorus -> (splice) -> last chorus line + ending        ~79 s
hype  1.5x  pass 2 chorus -> soft close (reveal) -> pass 3 verse -> pass 3 chorus -> ending ~60 s
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(os.path.join(HERE, "music", "love-analysis.json")))
BEATS, ONSETS = A["beats"], A["onsets"]
snap = lambda t: min(BEATS + ONSETS, key=lambda b: abs(b - t))
def beats_after(t, n):
    i = min(range(len(BEATS)), key=lambda k: abs(BEATS[k] - t)); return BEATS[i + n]

def plan(version):
    if version == "blend":  # same song path as calm, 1.2x; verse beats re-shared for the brisker read
        speed, segs, lead = 1.2, [(0.6, 59.44), (175.54, 196.0)], 0.45
        p0 = snap(18.3); chorus = snap(48.2)
        cuts = [("s1", 0.6), ("s2", snap(9.64)), ("s3", p0), ("bible", beats_after(p0, 4)), ("door", beats_after(p0, 9)),
                ("modes", beats_after(p0, 19)), ("lines", beats_after(p0, 28)), ("dash", chorus), ("visitor", beats_after(chorus, 5)),
                ("roll", beats_after(chorus, 10)), ("bday", 175.54), ("visit", snap(179.56)), ("s8", snap(185.2))]
    elif version == "calm":
        speed, segs, lead = 1.0, [(0.6, 59.44), (175.54, 196.0)], 0.6
        p0 = snap(18.3); chorus = snap(48.2)
        cuts = [("s1", 0.6), ("s2", snap(9.64)), ("s3", p0), ("bible", beats_after(p0, 4)), ("door", beats_after(p0, 10)),
                ("modes", beats_after(p0, 22)), ("lines", beats_after(p0, 29)), ("dash", chorus), ("visitor", beats_after(chorus, 5)),
                ("roll", beats_after(chorus, 10)), ("bday", 175.54), ("visit", snap(179.56)), ("s8", snap(185.2))]
    else:
        speed, segs, lead = 1.5, [(snap(106.2), 196.0)], 0.3
        p3 = snap(134.5); chorus = snap(164.4)
        cuts = [("s1", segs[0][0]), ("s2", beats_after(segs[0][0], 8)), ("s3", snap(126.3)), ("bible", p3),
                ("door", beats_after(p3, 6)), ("modes", beats_after(p3, 20)), ("lines", beats_after(p3, 28)), ("dash", chorus),
                ("visitor", beats_after(chorus, 5)), ("roll", beats_after(chorus, 10)), ("bday", 175.54),
                ("visit", snap(179.56)), ("s8", snap(185.2))]
    def vt(t):  # original song time -> video time
        acc = 0.0
        for a, b in segs:
            if a <= t <= b + 1e-6: return acc + (t - a) / speed
            acc += (b - a) / speed
        raise ValueError(t)
    total = sum(b - a for a, b in segs) / speed
    starts = [vt(t) for _, t in cuts] + [total]
    beat = 0.853 / speed
    # every beat (video time) inside each clip, for timing actions and sound effects
    grid = sorted({round(vt(b), 3) for b in BEATS if any(a <= b <= z for a, z in segs)})
    clips = [{"name": n, "start": round(starts[i], 3), "dur": round(starts[i + 1] - starts[i], 3), "beats": round((starts[i + 1] - starts[i]) / beat, 1)}
             for i, (n, _) in enumerate(cuts)]
    return {"version": version, "speed": speed, "segments": segs, "total": round(total, 3), "beat": beat, "lead": lead,
            "clips": clips, "grid": grid}

if __name__ == "__main__":
    for v in ("calm", "blend", "hype"):
        p = plan(v); json.dump(p, open(os.path.join(HERE, f"plan-{v}.json"), "w"), indent=1)
        print(f"{v}: {p['total']:.1f}s, beat {p['beat']:.3f}s")
        for c in p["clips"]: print(f"   {c['name']:8s} {c['start']:6.2f}  {c['dur']:5.2f}s  ({c['beats']} beats)")
