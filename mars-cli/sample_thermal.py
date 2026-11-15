#!/usr/bin/env python3
"""Add THEMIS thermal inertia (NASA/USGS quantitative 100 m mosaic) to viewer/point_values.json.
Reads only the 128x128-pixel tiles under each dot with HTTP range requests (no 2.5 GB downloads).
Units: J m-2 K-1 s-1/2 (tiu). Coverage: 60S-60N only; mosaic has gaps; absolute accuracy ~20% (Fergason 2006)."""
import json, math, os, re, struct, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://asc-astropedia.s3.us-west-2.amazonaws.com/Mars/Odyssey/THEMIS-Global-Thermal-Inertia-Mosaic/Quantitative-32-Bit/THEMIS_TI_Mosaic_Quant_%s_100mpp.cub"
SCALE = 592.74697523306
T = 128
meta, cache = {}, {}

def tilename(la, lo):
    lat0 = int(math.floor(la / 30.0)) * 30
    if lat0 < -60 or lat0 > 30: return None
    lon0 = int(math.floor((lo % 360) / 60.0)) * 60
    return ("%02dN" % lat0 if lat0 >= 0 else "%02dS" % -lat0) + "%03dE" % lon0

def rng(u, a, b):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"Range": "bytes=%d-%d" % (a, b)}), timeout=60).read()

def label(n):
    if n not in meta:
        t = rng(BASE % n, 0, 4000).decode("latin1")
        m = re.search(r"Group = Dimensions\s+Samples\s*=\s*(\d+)\s+Lines\s*=\s*(\d+)", t)
        mx = float(re.search(r"MaximumLatitude\s*=\s*([-\d.]+)", t).group(1))
        mn = float(re.search(r"MinimumLongitude\s*=\s*([-\d.]+)", t).group(1))
        meta[n] = (int(m.group(1)), int(m.group(2)), mx, mn)
    return meta[n]

def tile(n, ty, tx, nx):
    k = (n, ty, tx)
    if k not in cache:
        off = 65536 + (ty * nx + tx) * T * T * 4
        cache[k] = struct.unpack("<%df" % (T * T), rng(BASE % n, off, off + T * T * 4 - 1))
    return cache[k]

def sample(la, lo):
    n = tilename(la, lo)
    if not n: return None
    S, L, mx, mn = label(n)
    lo180 = ((lo + 180) % 360) - 180
    c = int((lo180 - mn) * SCALE); r = int((mx - la) * SCALE)
    if not (0 <= c < S and 0 <= r < L): return None
    nx = -(-S // T)
    tl = tile(n, r // T, c // T, nx)
    r0, c0 = r % T, c % T
    vals = []
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            rr, cc = r0 + dr, c0 + dc
            if 0 <= rr < T and 0 <= cc < T:
                v = tl[rr * T + cc]
                if math.isfinite(v) and -1e30 < v < 1e5 and v > 0: vals.append(v)
    if not vals: return None
    vals.sort()
    return {"v": int(round(vals[len(vals) // 2])), "lo": int(round(vals[0])), "hi": int(round(vals[-1])), "n": len(vals)}

if __name__ == "__main__":
    p = os.path.join(HERE, "viewer", "point_values.json")
    pv = json.load(open(p))
    keys = list(pv)
    def work(k):
        la, lo = map(float, k.split(","))
        try: return k, sample(la, lo)
        except Exception as e: return k, "ERR " + str(e)[:60]
    # prime labels sequentially (thread-safe), then sample in parallel
    for la in (-45, -15, 15, 45):
        for lo in range(0, 360, 60): label(tilename(la, lo + 1))
    done = bad = 0
    with ThreadPoolExecutor(12) as ex:
        for k, r in ex.map(work, keys):
            if isinstance(r, dict): pv[k]["ti"] = r; done += 1
            elif r: bad += 1; print(k, r, file=sys.stderr)
    json.dump(pv, open(p, "w"), separators=(",", ":"))
    print("thermal inertia added at", done, "of", len(keys), "locations; errors", bad)
