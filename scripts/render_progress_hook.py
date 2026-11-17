"""Runs inside Blender. Writes <out_dir>/progress.json while frames render, so
scripts/render_watch.py can show live progress from another terminal.

Usage in a render script:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import render_progress_hook as rp
    prog = rp.Progress(out_dir, frames, samples=sc.cycles.samples, res=(rx, ry))
    for f in frames:
        prog.frame_begin(f)          # before sc.frame_set(f): geometry is built there
        sc.frame_set(f)
        prog.stage("Rendering")
        bpy.ops.render.render(write_still=True)
        prog.frame_end(f)
    prog.finish()
"""
import json, os, re, time
import bpy

_SAMPLE = re.compile(r"Sample (\d+)/(\d+)")
_REMAIN = re.compile(r"Remaining: ([\d:.]+)")


def _secs(t):
    s = 0.0
    for part in t.split(":"):
        s = s * 60 + float(part)
    return s


class Progress:
    def __init__(self, out_dir, frames, samples=0, res=(0, 0)):
        os.makedirs(out_dir, exist_ok=True)
        self.path = os.path.join(out_dir, "progress.json")
        self.t0 = time.time()
        self.last_write = 0.0
        self.s = {
            "pid": os.getpid(),
            "blend": os.path.basename(bpy.data.filepath),
            "frames": list(frames),
            "res": list(res),
            "samples_setting": samples,
            "index": 0,                 # frames finished
            "frame": None,              # frame being worked on
            "stage": "Starting",
            "sample": 0,
            "samples": samples,
            "cycles_remaining": None,   # Cycles' own estimate for the current frame (s)
            "frame_started": None,
            "frame_times": {},          # frame -> seconds, whole frame (geometry + sync + trace + save)
            # In background mode Cycles traces in a few big batches (1 sample, then up to 512, then the
            # rest) and only reports between them, so the watcher fills the gaps from time:
            "trace_started": None,      # first "Sample" report of this frame
            "trace_end_est": None,      # absolute time Cycles expects path tracing to end
            "trace_times": {},          # frame -> seconds of path tracing (+ denoise)
            "started": self.t0,
            "updated": self.t0,
            "done": False,
            "error": None,
        }
        bpy.app.handlers.render_stats.append(self._on_stats)
        self._write(force=True)

    # --- Cycles' status line, e.g. "Remaining: 01:12.40 | Mem: 9.2G | Sample 37/192"
    def _on_stats(self, text, *_):   # Blender may pass a second argument
        now = time.time()
        stage = text.split("|")[-1].strip()
        m = _SAMPLE.search(text)
        if m:
            self.s["sample"], self.s["samples"] = int(m.group(1)), int(m.group(2))
            stage = "Path tracing"
            if self.s["trace_started"] is None:
                self.s["trace_started"] = now
        r = _REMAIN.search(text)
        if r:
            self.s["cycles_remaining"] = _secs(r.group(1))
            self.s["trace_end_est"] = now + self.s["cycles_remaining"]
        if stage.startswith("Finished"):
            stage = "Denoise / save"
            if self.s["trace_started"] and str(self.s["frame"]) not in self.s["trace_times"]:
                self.s["trace_times"][str(self.s["frame"])] = round(now - self.s["trace_started"], 1)
        changed = stage != self.s["stage"]
        self.s["stage"] = stage
        self._write(force=changed)

    def frame_begin(self, f):
        self.s.update(frame=f, frame_started=time.time(), sample=0, cycles_remaining=None,
                      trace_started=None, trace_end_est=None, stage="Building geometry (CPU)")
        self._write(force=True)

    def stage(self, text):
        self.s["stage"] = text
        self._write(force=True)

    def frame_end(self, f):
        self.s["frame_times"][str(f)] = round(time.time() - self.s["frame_started"], 1)
        self.s["index"] += 1
        self.s["stage"] = "Frame saved"
        self._write(force=True)

    def finish(self, error=None):
        self.s["done"] = True
        self.s["error"] = error
        self.s["stage"] = "Error" if error else "All frames done"
        self._write(force=True)
        if self._on_stats in bpy.app.handlers.render_stats:
            bpy.app.handlers.render_stats.remove(self._on_stats)

    def _write(self, force=False):
        now = time.time()
        if not force and now - self.last_write < 0.25:   # stats fire very often; 4 writes/s is plenty
            return
        self.last_write = now
        self.s["updated"] = now
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.s, fh)
            os.replace(tmp, self.path)
        except OSError:
            pass   # the watcher had the file open for a moment; the next update will land
