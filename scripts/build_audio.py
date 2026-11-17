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


def main():
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    # wind: a steady 40 s bed (loop) and the strongest 3 s as a gust one-shot
    w = load("wind.ogg")
    a = loudest(w, 3.0)
    save(level(fade(w[int(a * SR):int((a + 3.2) * SR)], 0.3, 1.2), -16), "wind_gust", 80)
    we = env(w, 1.0)
    quiet = min(range(0, len(w) - 42 * SR, SR * 2), key=lambda i: float(np.std(we[i:i + 42 * SR])))
    save(level(loop(w[quiet:quiet + 42 * SR], 3.0), -22), "wind_loop")

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

    # wooden door: the creak pitched down a little so it reads heavier (old carved door)
    d = load("door.ogg", rate=0.82)
    a = loudest(d, 2.6)
    save(level(fade(d[int(a * SR):int((a + 2.8) * SR)], 0.02, 0.6), -18), "door_creak", 80)

    # puja bell (ghanti)
    b = load("bell.flac")
    save(level(fade(b, 0.002, 0.8), -20), "bell", 80)

    # room drone: singing bowl an octave down, looped
    bw = load("bowl.ogg", rate=0.5)
    save(level(loop(bw, 2.5), -24), "room_drone")

    # kausi morning: dawn birds (South Indian recording), quietest-varying 40 s, looped
    dn = load("dawn.ogg")
    a = loudest(dn, 40.0)
    save(level(loop(dn[int(a * SR):int((a + 42) * SR)], 3.0), -24), "dawn_loop")


if __name__ == "__main__":
    sys.exit(main())
