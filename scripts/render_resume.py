"""Renders the frames of a range that are not on disk yet, and restarts Blender if it crashes
(e.g. HIP "Failed to build BLAS") or hangs (progress.json not updated for STALL_S seconds, e.g.
stuck at "Importance map"). After two failures the next attempts run with HIP RT off
(S01_NO_HIPRT=1); the images are the same, only the BVH build differs.

Run (from the repo root):
  python scripts/render_resume.py <blender.exe> <file.blend> <render_script.py> <out_dir> <first> <last> [res_x res_y] [--no-hiprt]
Live progress: python scripts/render_watch.py <out_dir>
"""
import json, os, subprocess, sys, time

args = [a for a in sys.argv[1:] if a != "--no-hiprt"]
blender, blend, script, out_dir = args[0:4]
first, last = int(args[4]), int(args[5])
res = args[6:8] or ["1920", "1080"]
MAX_ATTEMPTS = 12
# a frame takes ~50-90 s; progress.json is rewritten at every stage. RENDER_STALL_S raises it
# for scenes with a long silent first sync (s02: ~385 s of single-threaded object sync)
STALL_S = int(os.environ.get("RENDER_STALL_S", "300"))


def progress_age():
    try:
        with open(os.path.join(out_dir, "progress.json"), encoding="utf-8") as f:
            return time.time() - json.load(f)["updated"]
    except Exception:
        return 0.0

log_path = os.path.join(out_dir, "resume_log.txt")


def note(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def missing():
    return [f for f in range(first, last + 1)
            if not (os.path.isfile(p := os.path.join(out_dir, f"{f:04d}.png")) and os.path.getsize(p) > 0)]


failures = 0
no_hiprt = "--no-hiprt" in sys.argv
for attempt in range(1, MAX_ATTEMPTS + 1):
    todo = missing()
    if not todo:
        note(f"all frames {first}-{last} on disk")
        break
    env = dict(os.environ)
    if no_hiprt:
        env["S01_NO_HIPRT"] = "1"
    note(f"attempt {attempt}: {len(todo)} frames from {todo[0]}{' (HIP RT off)' if no_hiprt else ''}")
    with open(os.path.join(out_dir, f"stdout_attempt{attempt:02d}.txt"), "w", encoding="utf-8") as so:
        proc = subprocess.Popen([blender, "-b", blend, "--python", script, "--", out_dir,
                                 ",".join(map(str, todo)), *res], stdout=so, stderr=subprocess.STDOUT, env=env)
        started = time.time()
        while proc.poll() is None:
            time.sleep(15)
            # ignore the old progress.json until this Blender has written its own
            if time.time() - started > STALL_S and progress_age() > STALL_S:
                note(f"no progress for {STALL_S} s (hung): killing Blender pid {proc.pid}")
                proc.kill()
                proc.wait()
        code = proc.returncode
    left = missing()
    if not left:
        note(f"attempt {attempt} finished (exit {code}); all frames on disk")
        break
    failures += 1
    note(f"attempt {attempt} stopped (exit {code}) at frame {left[0]}; {len(left)} left")
    if failures >= 2 and not no_hiprt:
        no_hiprt = True
        note("second failure: HIP RT off from now on")
    time.sleep(10)    # let the driver recover
else:
    note(f"gave up after {MAX_ATTEMPTS} attempts; {len(missing())} frames missing")
