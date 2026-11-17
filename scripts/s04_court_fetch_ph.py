# Download Poly Haven (CC0) textures / HDRIs / models via the public API into blender/assets/polyhaven/.
#   python scripts/s04_court_fetch_ph.py tex <id> [res]      -> polyhaven/<id>_{diff,nor_gl,rough,disp}_<res>.jpg
#   python scripts/s04_court_fetch_ph.py hdri <id> [res]     -> polyhaven/<id>_<res>.hdr
#   python scripts/s04_court_fetch_ph.py model <id> [res]    -> polyhaven/models/<id>/<id>_<res>.gltf (+ bin, textures)
import sys, os, json, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets", "polyhaven")
UA = {"User-Agent": "asset-fetch/1.0"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()

def save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print("have", path); return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = get(url)
    with open(path, "wb") as f:
        f.write(data)
    print("got ", path, len(data) // 1024, "KB")

kind, aid = sys.argv[1], sys.argv[2]
res = sys.argv[3] if len(sys.argv) > 3 else ("2k" if kind != "model" else "1k")
files = json.loads(get("https://api.polyhaven.com/files/" + aid))
if kind == "tex":
    want = {"Diffuse": "diff", "nor_gl": "nor_gl", "Rough": "rough", "Displacement": "disp", "AO": "ao"}
    for key, short in want.items():
        if key in files and res in files[key]:
            f = files[key][res].get("jpg") or files[key][res].get("png")
            save(f["url"], os.path.join(ROOT, "%s_%s_%s.%s" % (aid, short, res, f["url"].rsplit(".", 1)[1])))
elif kind == "hdri":
    f = files["hdri"][res]["hdr"]
    save(f["url"], os.path.join(ROOT, "%s_%s.hdr" % (aid, res)))
elif kind == "model":
    g = files["gltf"][res]["gltf"]
    d = os.path.join(ROOT, "models", aid)
    save(g["url"], os.path.join(d, os.path.basename(g["url"])))
    for rel, inc in g.get("include", {}).items():
        save(inc["url"], os.path.join(d, rel))
