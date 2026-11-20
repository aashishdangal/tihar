"""Build the web sound set from the downloaded Commons originals (refrences/audio_src/).

Cuts one-shots, makes seamless loops (tail crossfaded into the head), evens the loudness and
encodes small mono MP3s into web/public/audio/. The mix (who plays when, how loud) lives in
web/src/audio.js. Credits for every source: CREDITS.md.

Run (repo root): python scripts/build_audio.py
"""
import json, os, subprocess, sys
import numpy as np

SRC = os.path.join("refrences", "audio_src")
OUT = os.path.join("web", "public", "audio")
SR = 44100
BLOW_SRC = "freesound_community-blowing-out-candlewav-14441.mp3"
BREATH_SRC = "u_hm3ohsiik6-breath-in-242641.mp3"
WINGS_SRC = "freesound_community-075692_bird-flying-awaywav-86143.mp3"
COUGH_SRC = "freesound_community-adult-male-coughing-45593.mp3"
SOB_SRC = "irenehebo-mujer_llorando-209276.mp3"
PANT_SRC = "fnx_sound-animated-dog-panting-287307.mp3"
MOO_SRC = "ribhavagrawal-cow-mooing-type-03-293302.mp3"
MOO2_SRC = "universfield-cow-moo-122255.mp3"
STEP_SRC = "eaglaxle-generic-footstep-2-530779.mp3"
MADAL_SRC = "freesound_community-bummm-75482.mp3"


def load(name, rate=1.0):
    """decode to mono float32 at SR; rate < 1 pitches down (and slows) like a tape"""
    af = f"asetrate={int(SR * rate)},aresample={SR}" if rate != 1.0 else f"aresample={SR}"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(SRC, name), "-ac", "1", "-af", af,
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def env(x, win=0.05):
    """moving RMS (cumulative sum: fast for any window length)"""
    n = max(1, int(SR * win))
    c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    m = (c[n:] - c[:-n]) / n
    pad = n // 2
    m = np.concatenate([np.full(pad, m[0]), m, np.full(len(x) - len(m) - pad, m[-1])])
    return np.sqrt(np.maximum(m, 0)).astype(np.float32)


def noise(n, seed=1):
    """the same cheap deterministic noise the browser engine uses, so builds are repeatable"""
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, n).astype(np.float32)


def fade(x, a=0.01, b=0.05):
    x = x.copy()
    na, nb = int(SR * a), int(SR * b)
    if na: x[:na] *= np.linspace(0, 1, na)
    if nb: x[-nb:] *= np.linspace(1, 0, nb)
    return x


def loop(x, xfade=2.0):
    """seamless loop: the last xfade seconds are blended (equal power) into the first"""
    n = int(SR * xfade)
    t = np.linspace(0, np.pi / 2, n)
    head, tail = x[:n], x[-n:]
    out = x[n:-n].copy() if len(x) > 3 * n else x.copy()
    blend = tail * np.cos(t) + head * np.sin(t)
    return np.concatenate([blend, out])


def level(x, rms_db=-20.0, peak_db=-1.0):
    r = np.sqrt(np.mean(x ** 2)) + 1e-9
    g = 10 ** (rms_db / 20) / r
    p = np.max(np.abs(x)) * g
    if p > 10 ** (peak_db / 20):
        g *= 10 ** (peak_db / 20) / p
    return (x * g).astype(np.float32)


def save(x, name, kbps=64):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", f"{kbps}k", path], input=x.tobytes(), check=True)
    print(f"{name:14s} {len(x) / SR:6.1f} s  {os.path.getsize(path) // 1024:5d} KB")


def loudest(x, length, step=0.25):
    """start (s) of the loudest window of `length` seconds"""
    e = env(x, 0.2)
    n, s = int(SR * length), int(SR * step)
    best = max(range(0, max(1, len(x) - n), s), key=lambda i: float(np.mean(e[i:i + n])))
    return best / SR


def smooth(x, n):
    """boxcar average over n samples, vectorised (cumulative sum)"""
    if n < 2:
        return x
    c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64))])
    m = (c[n:] - c[:-n]) / n
    pad = n // 2
    return np.concatenate([np.full(pad, m[0]), m, np.full(len(x) - len(m) - pad, m[-1])]).astype(np.float32)


def lp(x, hz):
    """low-pass: two boxcars in series. Takes the edge off, or pushes a sound into the distance."""
    n = max(1, int(0.44 * SR / hz))
    return smooth(smooth(x, n), n)


def hp(x, hz):
    """high-pass: whatever the low-pass did not keep (drops rumble and body)"""
    return (x - lp(x, hz)).astype(np.float32)


def squash(x, amount=0.6):
    """soft-clip the peaks: a campfire's big cracks become a small wick's ticks"""
    return np.tanh(x * (1 + amount * 3)).astype(np.float32) / (1 + amount * 3) ** 0.5


def steady(x, length):
    """start (s) of the most even window of `length` seconds (the least eventful stretch)"""
    e = env(x, 1.0)
    n = int(SR * length)
    if len(x) <= n:
        return 0.0
    best = min(range(0, len(x) - n, SR), key=lambda i: float(np.std(e[i:i + n])))
    return best / SR


def have(name):
    return os.path.exists(os.path.join(SRC, name))


def main():
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    # Each block runs only if its source is still in refrences/audio_src (git-ignored), so a
    # partial source folder rebuilds what it can instead of failing.

    if have("wind.ogg"):
    # wind: a steady 40 s bed (loop) and the strongest 3 s as a gust one-shot
        w = load("wind.ogg")
        a = loudest(w, 3.0)
        save(level(fade(w[int(a * SR):int((a + 3.2) * SR)], 0.3, 1.2), -16), "wind_gust", 80)
        we = env(w, 1.0)
        quiet = min(range(0, len(w) - 42 * SR, SR * 2), key=lambda i: float(np.std(we[i:i + 42 * SR])))
        save(level(loop(w[quiet:quiet + 42 * SR], 3.0), -22), "wind_loop")

    

    if have("crow.ogg"):
    # house crow: the two loudest caws as separate one-shots
        c = load("crow.ogg")
        e = env(c, 0.03)
        thr = 0.35 * e.max()
        on, caws = False, []
        for i in range(0, len(e), 64):
            if not on and e[i] > thr:
                on, s0 = True, i
            elif on and e[i] < thr * 0.5:
                on = False
                if i - s0 > SR * 0.08:
                    caws.append((float(e[s0:i].mean()), s0, i))
        caws = sorted(caws, reverse=True)[:3]
        caws = sorted(caws, key=lambda c3: c3[1])
        print("crow caws at", [round(s / SR, 2) for _, s, _ in caws])
        for k, (_, s0, s1) in enumerate(caws, 1):
            seg = c[max(0, s0 - int(0.03 * SR)):min(len(c), s1 + int(0.35 * SR))]
            save(level(fade(seg, 0.005, 0.25), -16), f"crow_caw{k}", 80)

    

    if have("door.ogg"):
    # wooden door: the creak pitched down a little so it reads heavier (old carved door)
        d = load("door.ogg", rate=0.82)
        a = loudest(d, 2.6)
        save(level(fade(d[int(a * SR):int((a + 2.8) * SR)], 0.02, 0.6), -18), "door_creak", 80)

    

    if have("bell.flac"):
    # puja bell (ghanti)
        b = load("bell.flac")
        save(level(fade(b, 0.002, 0.8), -20), "bell", 80)

    

    if have("bowl.ogg"):
    # room drone: singing bowl an octave down, looped
        bw = load("bowl.ogg", rate=0.5)
        save(level(loop(bw, 2.5), -24), "room_drone")

    

    if have("dawn.ogg"):
    # kausi morning: dawn birds (South Indian recording), quietest-varying 40 s, looped
        dn = load("dawn.ogg")
        a = loudest(dn, 40.0)
        save(level(loop(dn[int(a * SR):int((a + 42) * SR)], 3.0), -24), "dawn_loop")

    # ---- the diyo flame (s00 gate) -------------------------------------------------------
    # A clay diyo is an oil wick: it does not crackle (wood pops because of trapped steam) and
    # it is nearly silent a hand's width away — owner, 2026-11-19. So the campfire is stripped
    # of everything that makes it a fire: the rumble goes, then the signal is divided by its own
    # envelope so every pop and crack flattens out, and what is left is low-passed to a soft
    # flutter of air. Kept in the mix at a tenth of the old level.
    if have("flame.ogg"):
        f = load("flame.ogg")
        a = steady(f, 20.0)
        seg = hp(f[int(a * SR):int((a + 22) * SR)], 110)
        e = env(seg, 0.005)
        flat = seg / (e + 1e-4) * float(np.mean(e))        # no transient survives this
        r = float(np.sqrt(np.mean(flat ** 2)))
        flat = np.tanh(flat / (r * 2.5)) * (r * 2.5)       # and nothing peaks back out
        slow = env(seg, 1.5)                                # the flame's own slow breathing
        slow = slow / (float(np.mean(slow)) + 1e-9)
        seg = lp(flat, 900) * (0.82 + 0.3 * slow).astype(np.float32)
        # measured on the result: crest ~7 dB (a fire is 18-25), centroid ~450 Hz
        save(level(loop(seg.astype(np.float32), 2.0), -26), "flame_loop")

    # ---- blowing the diyo out (s00 blow-out) -----------------------------------------------
    # Owner-supplied recording (2026-11-19), replacing the generated breath. The take has 0.29 s
    # of room before the puff; on a cue that lands a third of a second late, so it is trimmed to
    # 20 ms before the breath starts and the tail is kept whole.
    if have(BLOW_SRC):
        bl = load(BLOW_SRC)
        e = env(bl, 0.02)
        on = np.where(e > 0.15 * e.max())[0]
        a0 = max(0, on[0] - int(0.02 * SR))
        save(level(fade(bl[a0:], 0.004, 0.08), -16), "blow", 80)

    # ---- breathing in at the gate (s00, the सुरु control) ----------------------------------
    # Owner-supplied (2026-11-19, Pixabay). Held while the boy fills his lungs, cut off by the
    # blow, so the front is trimmed to the breath itself and the end is left alone — the blow
    # ends it, never a fade. Kept soft: this is a face a hand's width from the diyo.
    if have(BREATH_SRC):
        br = load(BREATH_SRC)
        e = env(br, 0.02)
        on = np.where(e > 0.15 * e.max())[0]
        a0 = max(0, on[0] - int(0.03 * SR))
        save(level(fade(br[a0:], 0.03, 0.05), -24), "breath_in", 80)

    # ---- the valley at night (s01, carried into s02) ---------------------------------------
    # Owner, 2026-11-19: "distant noise only, recognizable not hearable clearly", and it must not
    # loop too soon. So: 90 s (a pass of s01 never reaches the seam), several sources laid over
    # each other at different offsets so nothing lines up, and everything low-passed to 700 Hz —
    # distance is a low-pass filter. Nothing in here should be identifiable on its own.
    if have("city_a.ogg") and have("city_b.ogg"):
        LEN = 90.0
        n = int(LEN * SR)

        def take(name, start_s, rate=1.0):
            x = load(name, rate=rate)
            a = int(start_s * SR)
            if len(x) < a + n:                      # wrap short sources rather than pad silence
                x = np.tile(x, int(np.ceil((a + n) / len(x))))
            return x[a:a + n]

        bed = take("city_a.ogg", 20.0) * 0.9
        bed += take("city_b.ogg", 95.0) * 0.8       # a different offset: the two never line up
        if have("street_sa.mp3"):                   # a South Asian street under it, far off
            bed += take("street_sa.mp3", 8.0) * 0.35

        # scattered events: horns and one child, placed by hand so they never land together
        def drop(x, at_s, gain):
            a = int(at_s * SR)
            k = min(len(x), n - a)
            if k > 0:
                bed[a:a + k] += fade(x[:k], 0.02, 0.3) * gain

        if have("horn.wav"):
            h = load("horn.wav")
            for at, g, r in ((11.3, 0.18, 1.0), (38.9, 0.12, 0.92), (57.4, 0.15, 1.07), (78.1, 0.1, 0.97)):
                drop(load("horn.wav", rate=r), at, g)
        if have("childcry.ogg"):
            c = load("childcry.ogg")
            a = loudest(c, 3.0)
            drop(c[int(a * SR):int((a + 3.0) * SR)], 46.2, 0.14)

        bed = lp(bed.astype(np.float32), 700)       # the whole valley, heard from above
        save(level(loop(bed, 3.0), -30), "city_night", 56)

    # ---- one aeroplane, far away (s01) -----------------------------------------------------
    # Mostly rumble by the time it reaches a hill: low-passed hard and faded in and out long, so
    # it arrives and leaves rather than starting.
    if have("plane.ogg"):
        pl = load("plane.ogg")
        a = loudest(pl, 9.0)
        save(level(fade(lp(pl[int(a * SR):int((a + 10) * SR)], 500), 2.0, 2.5), -24), "plane_far", 64)

    # ---- a child, somewhere down there (s01) -----------------------------------------------
    if have("childcry.ogg"):
        c = load("childcry.ogg")
        a = loudest(c, 2.6)
        save(level(fade(lp(c[int(a * SR):int((a + 2.8) * SR)], 1100), 0.15, 0.8), -28), "child_far", 64)

    # ---- the crow leaving the branch (s02, frame 30) ---------------------------------------
    # Owner-supplied (2026-11-19), replacing the generated wingbeats. The crow is never seen
    # flying — this is the whole event — so the take is trimmed to the wingbeats themselves.
    # The source peaks a little over 0 dBFS; level() pulls it to -1 dB peak.
    if have(WINGS_SRC):
        wg = load(WINGS_SRC)
        e = env(wg, 0.02)
        on = np.where(e > 0.12 * e.max())[0]
        a0 = max(0, on[0] - int(0.02 * SR))
        save(level(fade(wg[a0:], 0.005, 0.25), -16), "wings", 80)

    # ---- the dying king and his sister (s02 chamber) ---------------------------------------
    # Owner-supplied (2026-11-19). Both takes are close-mic'd and bright (centroids ~3.8 kHz and
    # ~3.6 kHz); in the scene the king is turned to the wall behind a crown in soft focus and
    # Jamuna is seen from behind, so the sound has to sit behind cloth and distance too — rule 6
    # applies to the mix as much as to the frame. Low-passed hard, pitched down, kept quiet.
    if have(COUGH_SRC):
        cg = load(COUGH_SRC, rate=0.88)          # an old man, not a healthy one
        # the three coughs in the take, cut apart: the full one, then the small dry one
        save(level(fade(lp(cg[int(0.10 / 0.88 * SR):int(1.05 / 0.88 * SR)], 1400), 0.01, 0.35), -26), "cough", 80)
        save(level(fade(lp(cg[int(1.34 / 0.88 * SR):int(1.62 / 0.88 * SR)], 1200), 0.01, 0.3), -29), "cough_small", 80)
    if have(SOB_SRC):
        sb2 = load(SOB_SRC)
        # three sobs, not five: enough to know she is crying, not enough to perform it
        save(level(fade(lp(sb2[int(0.85 * SR):int(3.55 * SR)], 1900), 0.08, 0.6), -28), "sob", 80)

    # ---- the morning over the rooftops (s02, out through the door) --------------------------
    # The dawn chorus was doing all the work here and it is a South Indian recording — too many
    # birds for a Kathmandu kausi (owner, 2026-11-19). A conch from across the rooftops and a
    # rooster some way off carry the morning instead, both pushed into the distance.
    if have("conch.ogg"):
        cn = load("conch.ogg")
        save(level(fade(lp(cn[:int(4.2 * SR)], 900), 0.25, 1.6), -23), "conch_far", 72)
    if have("rooster.ogg"):
        rs = load("rooster.ogg", rate=0.95)
        a = loudest(rs, 2.0)
        save(level(fade(lp(rs[int(a * SR):int((a + 2.2) * SR)], 1500), 0.05, 0.7), -26), "rooster_far", 72)

    # ---- the dog panting (s04) -------------------------------------------------------------
    # Owner-supplied (2026-11-19), replacing the generated panting. It loops under the whole
    # scene, so the cut has to be a whole number of breaths or the loop point lands mid-pant:
    # the take runs at ~1.38 s a cycle, so six cycles are kept and crossfaded inside one.
    if have(PANT_SRC):
        pt = load(PANT_SRC)
        e = env(pt, 0.02)
        on = np.where(e > 0.1 * e.max())[0]
        body = pt[on[0]:on[-1]]
        # measure the cycle on this take rather than trusting a fixed number
        ee = (env(body, 0.02) - np.mean(env(body, 0.02))).astype(np.float64)
        m = min(len(ee), SR * 6)
        ac = np.correlate(ee[:m], ee[:m], "full")[m - 1:]
        lo, hi = int(SR * 0.25), int(SR * 1.6)
        per = (lo + int(np.argmax(ac[lo:hi]))) / SR
        cycles = max(1, int((len(body) / SR) // per))
        seg = body[:int(cycles * per * SR)]
        save(level(loop(lp(seg, 3500), min(0.5, per * 0.35)), -28), "dog_breath")
        print(f"   (panting: {per:.2f} s a breath, {cycles} kept)")

    # ---- the cow mooing (s05) ---------------------------------------------------------------
    # The animation moos twice, the first long and the second short (owner, 2026-11-19), and the
    # owner supplied a take for each. They are different recordings but land within 25 Hz of each
    # other (1158 and 1135 Hz centroid), so they read as one animal rather than two. Both takes
    # clip a little over 0 dBFS; level() pulls them to -1 dB peak.
    if have(MOO_SRC):
        mo = load(MOO_SRC)
        save(level(fade(mo[int(0.86 * SR):int(2.30 * SR)], 0.02, 0.35), -18), "cow_moo", 80)
    if have(MOO2_SRC):
        m2 = load(MOO2_SRC)
        save(level(fade(m2[int(0.55 * SR):int(1.60 * SR)], 0.02, 0.3), -19), "cow_moo_short", 80)

    # ---- Laxmi's footsteps (s05, frames 100-135) --------------------------------------------
    # Owner-supplied (2026-11-19). These are not a person walking: golden footprints appear one
    # by one on the brick and bloom with light. The take is a bright, hard-surfaced step
    # (centroid 3.2 kHz); low-passed to 2 kHz it becomes a bare foot on old brick, which is what
    # the picture shows. The step itself is only 90 ms, so it is cut tight.
    if have(STEP_SRC):
        st = load(STEP_SRC)
        e = env(st, 0.01)
        on = np.where(e > 0.1 * e.max())[0]
        a0 = max(0, on[0] - int(0.01 * SR))
        save(level(fade(lp(st[a0:on[-1] + int(0.18 * SR)], 2000), 0.003, 0.12), -22), "step", 72)

    # ---- Laxmi arriving (s05, frame 138) -----------------------------------------------------
    # "A divine sound effect" (owner, 2026-11-19). Everything else in this site is a real
    # recording, so a synth sparkle would be the one fake thing in it. This is built from the
    # physics of a struck bowl instead: inharmonic partials (a bowl is not a sawtooth — its
    # overtones sit at 2.0, 3.01, 4.17, 5.43 times the fundamental, which is why it shimmers
    # rather than buzzes), a long reverse swell leading in so she arrives rather than appears,
    # and a slow beat between two slightly detuned voices for the shimmer. Tuned to C, the key
    # of the harmonium drone already under the scene, so it lands in the same world.
    if True:
        LEN, F0 = 7.0, 261.63                      # C4, the harmonium's root two octaves up
        n = int(LEN * SR)
        t = np.arange(n) / SR
        PARTIALS = [(1.0, 1.0), (2.0, 0.5), (3.01, 0.32), (4.17, 0.18), (5.43, 0.12), (7.09, 0.06)]
        strike = int(2.2 * SR)                     # the swell leads in for 2.2 s, then it rings
        y = np.zeros(n)
        for mult, amp in PARTIALS:
            for detune in (-0.6, 0.6):             # two voices, beating slowly: the shimmer
                ph = 2 * np.pi * (F0 * mult + detune) * t
                decay = np.exp(-(t - t[strike]) / (3.2 / mult ** 0.6))   # highs die first, as they do
                decay[:strike] = 0
                y += np.sin(ph) * amp * decay
        # the reverse swell: the room filling before the strike
        sw = np.zeros(n)
        rise = np.linspace(0, 1, strike) ** 2.6
        for mult, amp in PARTIALS[:3]:
            sw[:strike] += np.sin(2 * np.pi * F0 * mult * t[:strike]) * amp * rise
        y += sw * 0.33
        y = lp(y.astype(np.float32), 5200)         # take the glassy top off
        save(level(fade(y, 0.05, 1.2), -24), "divine", 88)

    # ---- the offering on the thali (s06) -----------------------------------------------------
    # The scene ends looking down into the plate: money, flowers, fruit, diyos. The giving is
    # the point of Deusi, so the coins are the one physical event in it (owner, 2026-11-19).
    # A coin on brass is two things at once — a bright inharmonic ping from the coin, and the
    # plate's own low mode ringing underneath because the coin struck it.
    if True:
        def coin(f0, plate, length=0.9, seed=5):
            n = int(length * SR)
            t = np.arange(n) / SR
            y = np.zeros(n)
            for mult, amp, dec in ((1.0, 1.0, 0.22), (2.13, 0.6, 0.15), (3.41, 0.33, 0.1), (4.9, 0.18, 0.07)):
                y += np.sin(2 * np.pi * f0 * mult * t) * amp * np.exp(-t / dec)
            # the plate it lands in: a lower, longer mode, struck softly
            for mult, amp, dec in ((1.0, 0.5, 0.75), (2.76, 0.22, 0.4)):
                y += np.sin(2 * np.pi * plate * mult * t) * amp * np.exp(-t / dec)
            z = noise(n, seed)                       # the contact itself, 2 ms of it
            y[:int(0.002 * SR)] += z[:int(0.002 * SR)] * 2.0
            return y.astype(np.float32)

        save(level(fade(coin(2380, 430, seed=5), 0.0005, 0.25), -20), "coin", 72)
        save(level(fade(coin(2810, 455, seed=13), 0.0005, 0.25), -21), "coin2", 72)

        # flower heads and a little rice going in after the coins: dry, soft, no ring at all
        n = int(0.7 * SR)
        z = noise(n, 23)
        pet = np.zeros(n)
        for t0 in (0.0, 0.035, 0.062, 0.098, 0.131, 0.176, 0.22, 0.27, 0.33):
            at = int(t0 * SR)
            ln = int(SR * (0.04 + 0.05 * ((t0 * 41) % 1)))
            seg = lp(z[at:at + ln] if at + ln < n else z[:ln], 2600)
            w = np.sin(np.pi * np.arange(len(seg)) / len(seg)) ** 2
            pet[at:at + len(seg)] += seg * w * 1.6
        for k in range(26):                          # grains of rice, tiny and dry
            at = int((0.05 + 0.5 * ((k * 0.37) % 1)) * SR)
            ln = int(0.004 * SR)
            if at + ln < n:
                pet[at:at + ln] += z[(k * 977) % (n - ln):(k * 977) % (n - ln) + ln] * 0.5 * np.exp(-np.arange(ln) / (ln / 3))
        save(level(fade(lp(pet.astype(np.float32), 5000), 0.004, 0.3), -24), "petals", 72)

    # ---- madal and clapping (s06) -------------------------------------------------------------
    # No Deusi voices (owner, 2026-11-19): the drum and the clapping carry the scene. From inside
    # a courtyard that is what actually reaches you — words blur down a lane long before a beat.
    # The madal is the owner's recording (2026-11-19), replacing a synthesized one.
    #
    # Both files MUST come out the same length: they are separate loops started at the same
    # moment, so equal length is what keeps the clapping with the drum instead of drifting off it
    # after a few bars. The clap tempo is measured from the drum, never assumed.
    per, total = 60.0 / 100.0 * 4, None                 # fallback if there is no recording
    if have(MADAL_SRC):
        md = load(MADAL_SRC)
        e = env(md, 0.01)
        on = np.where(e > 0.12 * e.max())[0]
        body = md[on[0]:]
        ee = (env(body, 0.01) - float(np.mean(env(body, 0.01)))).astype(np.float64)
        m = min(len(ee), SR * 8)
        ac = np.correlate(ee[:m], ee[:m], "full")[m - 1:]
        lo, hi = int(SR * 0.4), int(SR * 3.0)
        per = (lo + int(np.argmax(ac[lo:hi]))) / SR     # the drum's own cycle
        cycles = max(1, int((len(body) / SR) // per))
        total = int(cycles * per * SR)
        save(level(fade(body[:total], 0.004, 0.0), -24), "madal_loop", 72)
        print(f"   (madal: {per:.2f} s a cycle, {cycles} kept = {cycles * per:.1f} s)")

    # the clapping: several pairs of hands, never quite together, on the drum's own beat. A clap
    # is a short burst of noise with a small cupped-air body; the scatter between people is what
    # sells it — people clapping together is a sample, people nearly together is a crowd.
    if total:
        rng = np.random.default_rng(7)
        clp = np.zeros(total)
        beat = per / 2                                   # twice a cycle, as a group claps
        t0 = 0.0
        while t0 < total / SR - 0.4:
            for _ in range(5):                           # five pairs of hands
                at = int(max(0, t0 + rng.normal(0, 0.028)) * SR)
                mlen = int(0.09 * SR)
                z = rng.uniform(-1, 1, mlen)
                loI, band = 0.0, np.empty(mlen)
                for i in range(mlen):                    # band ~900-3500 Hz
                    loI += (z[i] - loI) * 0.33
                    band[i] = z[i] - loI
                envc = np.exp(-np.arange(mlen) / (SR * rng.uniform(0.004, 0.009)))
                cup = np.sin(2 * np.pi * rng.uniform(420, 760) * np.arange(mlen) / SR) * 0.25
                hit = (band + cup) * envc * rng.uniform(0.5, 1.0)
                k = min(mlen, total - at)
                if k > 0:
                    clp[at:at + k] += hit[:k]
            t0 += beat
        save(level(lp(clp.astype(np.float32), 4200), -27), "clap_loop", 72)

    # ---- the puja ghanta (s07) ----------------------------------------------------------------
    # A real brass ghanta, the bell used in Hindu ritual (owner, 2026-11-19: the thin Bell-ring
    # that was here read as a bicycle bell). The take has six strikes; the one at 17.64 s is the
    # strongest with a clean 7 s of room after it, so its tail is kept whole — the tail is what
    # separates a ghanta from a ping.
    if have("ghanta.wav"):
        gh = load("ghanta.wav")
        save(level(fade(gh[int(17.60 * SR):int(22.60 * SR)], 0.002, 1.8), -20), "ghanta", 80)

    # ---- cow bell (s05 goth) ---------------------------------------------------------------
    # One animal shifting its weight, not a herd on a mountain: the loudest cluster, warmed.
    if have("cowbell.ogg"):
        cb = load("cowbell.ogg", rate=0.92)
        a = loudest(cb, 3.0)
        save(level(fade(lp(cb[int(a * SR):int((a + 3.2) * SR)], 7000), 0.01, 0.7), -18), "cow_bell", 80)

    # ---- harmonium drone (s05 lamps) -------------------------------------------------------
    # One chord an octave down, filtered to its body and looped long: worship somewhere in the
    # house, never a tune anyone could hum back.
    if have("harmonium.wav"):
        h = load("harmonium.wav", rate=0.5)
        save(level(loop(lp(h, 900), 1.6), -30), "harmonium_drone")

    # ---- fireworks over the valley (s08) ---------------------------------------------------
    # Distance is a low-pass: all that reaches a hill is the thud, never the crack.
    if have("fireworks_a.ogg"):
        fa = load("fireworks_a.ogg")
        a = steady(fa, 30.0)
        save(level(loop(lp(fa[int(a * SR):int((a + 32) * SR)], 850), 2.5), -26), "fw_far_loop")
    if have("fireworks_b.ogg"):
        fb = load("fireworks_b.ogg")
        a = loudest(fb, 2.4)
        save(level(fade(lp(fb[int(a * SR):int((a + 2.6) * SR)], 1300), 0.01, 0.9), -17), "fw_burst", 80)

    # ---- village morning (s04 courtyard) ---------------------------------------------------
    # Dogs, birds and crickets at first light, recorded in South Asia: the right geography.
    if have("village.wav"):
        v = load("village.wav")
        a = steady(v, 40.0)
        save(level(loop(v[int(a * SR):int((a + 42) * SR)], 3.0), -25), "village_morning")


if __name__ == "__main__":
    sys.exit(main())
