"""Live render progress in the terminal. Reads <out_dir>/progress.json written by
scripts/render_progress_hook.py inside Blender.

Run:  python scripts/render_watch.py renders/s01_hero/test/v041_cycles
Ctrl+C closes the viewer only; the render keeps going.

In background mode Cycles traces in a few big batches (1 sample, then up to 512, then the rest)
and only reports between them. So within a frame the bar is time-based: from Cycles' own
estimate on the first frame, from the measured path-tracing time of earlier frames after that.
Estimated values are marked with ≈.
"""
import ctypes, json, os, sys, time

out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
path = os.path.join(out_dir, "progress.json")
os.system("")                              # turn on ANSI colours / cursor control in the Windows console
sys.stdout.reconfigure(encoding="utf-8")   # the bar characters aren't in cp1252

GOLD, DIM, RED, GREEN, RST = "\033[38;2;242;163;58m", "\033[2m", "\033[31m", "\033[32m", "\033[0m"
PREP, TRACE, SAVE = "prep", "trace", "save"   # share of a frame: geometry+sync / path tracing / denoise+save


def alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == 259                # STILL_ACTIVE


def bar(frac, width=40):
    frac = max(0.0, min(1.0, frac))
    n = int(frac * width)
    return GOLD + "█" * n + DIM + "░" * (width - n) + RST


def hms(s):
    if s is None:
        return "--:--"
    s = int(max(0, s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def mean(d):
    v = list(d.values())
    return sum(v) / len(v) if v else None


def current_frame(p, now):
    """(fraction of this frame done, seconds left on it, is_estimate)"""
    started = p["frame_started"] or now
    on_frame = now - started
    avg_frame, avg_trace = mean(p["frame_times"]), mean(p["trace_times"])
    st = p["stage"]

    if st in ("Frame saved",):
        return 1.0, 0.0, False
    if st == "Denoise / save":
        return 0.97, 3.0, True

    if st == "Path tracing" and p["trace_started"]:
        t = now - p["trace_started"]
        if avg_trace:                                   # earlier frames: best guide
            expected = avg_trace
        elif p["trace_end_est"]:                        # first frame: Cycles' own guess
            expected = p["trace_end_est"] - p["trace_started"]
        else:
            expected = None
        known = p["sample"] / p["samples"] if p["samples"] else 0
        tf = max(known, min(t / expected, 0.99)) if expected else known
        prep = p["trace_started"] - started
        # whole-frame fraction: prep done, trace tf of the way, save left
        if avg_frame and avg_trace:
            total = prep + avg_trace + max(2.0, avg_frame - avg_trace - prep)
        else:
            total = prep + (expected or 0) + 3.0
        left = max(0.0, (expected or 0) - t) + 3.0 if expected else None
        frac = min(0.99, (prep + tf * (expected or 0)) / total) if expected else tf
        return frac, left, True

    # building geometry / syncing to the GPU: no sample info yet
    if avg_frame:
        return min(0.99, on_frame / avg_frame) * 0.3, max(0.0, avg_frame - on_frame), True
    return 0.0, None, True


def draw(lines):
    sys.stdout.write("\033[H\033[J" + "\n".join(lines) + "\n")
    sys.stdout.flush()


started = time.time()
try:
    while True:
        try:
            with open(path, encoding="utf-8") as fh:
                p = json.load(fh)
        except (OSError, ValueError):
            draw([f"{GOLD}Render progress{RST}", "",
                  f"Waiting for {path}",
                  f"{DIM}Blender is opening the .blend (~15 s), or the render hasn't started yet. "
                  f"Waited {hms(time.time() - started)}{RST}"])
            time.sleep(1)
            continue

        now = time.time()
        n = len(p["frames"])
        done = p["index"]
        avg_frame = mean(p["frame_times"])

        if p["done"]:
            ff, left_frame, est = 0.0, 0.0, False
        else:
            ff, left_frame, est = current_frame(p, now)
        overall = (done + ff) / n if n else 0

        if p["done"]:
            eta = 0
        elif left_frame is None:
            eta = None
        else:
            per_frame = avg_frame or ((now - p["frame_started"]) + left_frame if p["frame_started"] else None)
            eta = left_frame + (per_frame or 0) * (n - done - 1)

        running = alive(p["pid"])
        quiet = now - p["updated"]
        tracing = p["stage"] == "Path tracing"
        if p["done"]:
            status = (RED + "Stopped with an error: " + str(p["error"]) + RST) if p["error"] else (GREEN + "All frames done" + RST)
        elif not running:
            status = RED + "Blender is no longer running (crashed or was closed)" + RST
        elif quiet > 90 and not tracing:
            status = RED + f"No update for {hms(quiet)} (stage: {p['stage']})" + RST
        elif tracing and p["trace_started"] and avg_frame is None and p["trace_end_est"] and now > p["trace_end_est"] + 60:
            status = GOLD + "Path tracing is taking longer than Cycles guessed (normal on frame 1)" + RST
        else:
            status = "Rendering"

        a = "≈" if est and not p["done"] else ""
        res = "x".join(str(v) for v in p["res"])
        lines = [
            f"{GOLD}Render progress{RST}  {p['blend']}  {res}  {p['samples_setting']} spp",
            "",
            f"All frames  {bar(overall)} {a}{overall * 100:5.1f} %   {done}/{n} frames",
            f"            elapsed {hms(now - p['started'])}   left {a}{hms(eta)}"
            + (f"   finish {a}{time.strftime('%H:%M', time.localtime(now + eta))}" if eta else ""),
            "",
        ]
        if not p["done"] and p["frame"] is not None:
            samp = f"Cycles reports sample {p['sample']}/{p['samples']}" if tracing and p["sample"] else ""
            lines += [
                f"Frame {p['frame']:>4}  {bar(ff)} {a}{ff * 100:5.1f} %   {samp}",
                f"            stage: {p['stage'][:70]}",
                f"            on this frame {hms(now - p['frame_started'])}   left {a}{hms(left_frame)}",
                "",
            ]
        if p["frame_times"]:
            lines.append("Finished:   " + "   ".join(
                f"{f}: {hms(t)}" + (f" ({hms(p['trace_times'][f])} tracing)" if f in p["trace_times"] else "")
                for f, t in p["frame_times"].items()))
            lines.append("")
        if not p["done"] and not p["frame_times"]:
            lines.append(f"{DIM}Cycles reports samples in big batches, so the bar runs on time (≈).{RST}")
        lines.append(status + f"{DIM}   (Ctrl+C closes this view, not the render){RST}")
        draw(lines)

        if p["done"] or not running:
            break
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
