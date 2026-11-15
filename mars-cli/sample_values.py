#!/usr/bin/env python3
"""Sample NASA global rasters at every viewer dot and write viewer/point_values.json.
Run once (needs numpy + tifffile; the big rasters are not shipped):
  python3 sample_values.py --dem Mars_MGS_MOLA_DEM_mosaic_global_463m.tif --albedo Mars_MGS_TES_Albedo_mosaic_global_7410m.tif
Every value is measured/derived from the raster named in `src`; nothing is invented."""
import argparse, json, math, os, re
import numpy as np, tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
R = 3396190.0

def load_points():
    s = open(os.path.join(HERE, "viewer", "data.js")).read()
    return json.loads(s[s.index("=") + 1:s.rindex(";")])["points"]

def key(la, lo): return "%.4f,%.4f" % (la, lo)

def terrain(dem, la, lo, half=5):
    """elevation, Horn slope (~0.9 km), plane-fit slope + residual roughness + relief over ~5 km window"""
    H, W = dem.shape
    px = 360.0 / W                                # degrees per pixel (463.09 m at the equator)
    r = (90 - la) / px; c = ((lo + 180) % 360) / px
    r0, c0 = int(r), int(c) % W
    if r0 - half < 0 or r0 + half >= H: return None
    cols = [(c0 + k) % W for k in range(-half, half + 1)]
    win = dem[r0 - half:r0 + half + 1][:, cols].astype(np.float64)
    if (win == -32768).any(): return None
    dy = px * math.pi / 180 * R
    dx = max(dy * math.cos(math.radians(la)), 1.0)
    z = win; m = half
    a = z[m-1:m+2, m-1:m+2]
    gx = ((a[0,2] + 2*a[1,2] + a[2,2]) - (a[0,0] + 2*a[1,0] + a[2,0])) / (8*dx)
    gy = ((a[2,0] + 2*a[2,1] + a[2,2]) - (a[0,0] + 2*a[0,1] + a[0,2])) / (8*dy)
    horn = math.degrees(math.atan(math.hypot(gx, gy)))
    X, Y = np.meshgrid((np.arange(-half, half+1))*dx, (np.arange(-half, half+1))*dy)
    A = np.c_[X.ravel(), Y.ravel(), np.ones(X.size)]
    coef, *_ = np.linalg.lstsq(A, z.ravel(), rcond=None)
    res = z.ravel() - A @ coef
    return {"el": int(round(z[m, m])), "slope1": round(horn, 1),
            "slope5": round(math.degrees(math.atan(math.hypot(coef[0], coef[1]))), 1),
            "rough": int(round(float(res.std()))), "relief": int(z.max() - z.min()),
            "win_km": round((2*half+1) * dy / 1000, 1)}

def albedo(a, la, lo, W=2880):
    H = a.shape[0]
    r = int(min(H-1, max(0, (90 - la) / 180 * H))); c = int(((lo + 180) % 360) / 360 * a.shape[1]) % a.shape[1]
    v = float(a[r, c])
    return None if v < -1e30 or not math.isfinite(v) else round(v, 3)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem", required=True); ap.add_argument("--albedo"); ap.add_argument("--geology")
    a = ap.parse_args()
    pts = load_points()
    dem = tifffile.memmap(a.dem)
    alb = tifffile.imread(a.albedo) if a.albedo else None
    geo = None
    if a.geology:
        import shapefile
        from shapely.geometry import shape, Point
        from shapely.strtree import STRtree
        rd = shapefile.Reader(a.geology)
        geoms = [shape(x.__geo_interface__) for x in rd.shapes()]
        recs = [r.as_dict() for r in rd.records()]
        tree = STRtree(geoms)
        def geo(la, lo):
            lo = ((lo + 180) % 360) - 180
            pt = Point(lo, la)
            for i in tree.query(pt):
                if geoms[i].contains(pt):
                    return {"u": recs[i]["Unit"], "d": recs[i]["UnitDesc"]}
            return None
    def arr(kind_prefix):
        q = [p for p in pts if p["k"].startswith(kind_prefix)]
        return q, np.radians([p["la"] for p in q]), np.radians([p["lo"] for p in q])
    def near(la, lo, q, qla, qlo):
        if not q: return None, None
        la, lo = math.radians(la), math.radians(lo)
        c = np.sin(la)*np.sin(qla) + np.cos(la)*np.cos(qla)*np.cos(qlo-lo)
        d = np.arccos(np.clip(c, -1, 1)) * 3389.5
        return d, q
    caves, cla, clo = arr("cave candidate")
    lands, lla, llo = arr("lander")
    cands, kla, klo = arr("candidate")
    out = {}
    for p in pts:
        k = key(p["la"], p["lo"])
        if k in out: continue
        v = {}
        t = terrain(dem, p["la"], p["lo"])
        if t: v["t"] = t
        if alb is not None:
            al = albedo(alb, p["la"], p["lo"])
            if al is not None: v["alb"] = al
        if geo:
            g = geo(p["la"], p["lo"])
            if g: v["g"] = g
        d, q = near(p["la"], p["lo"], caves, cla, clo)
        if d is not None:
            o = d.copy()
            if p["k"].startswith("cave candidate"):
                o[o < 0.5] = 1e9                       # ignore the record itself
            i = int(o.argmin())
            v["c"] = {"n100": int((d <= 100).sum()) - (1 if p["k"].startswith("cave candidate") else 0),
                      "d": round(float(o[i]), 1), "id": q[i]["n"], "t": q[i]["k"].split("(")[-1].rstrip(")"),
                      "pr": q[i]["i"][0].split(" ")[1]}
        d, q = near(p["la"], p["lo"], lands, lla, llo)
        o = {}
        if d is not None:
            ok = d.copy()
            if p["k"].startswith("lander"): ok[ok < 0.5] = 1e9
            i = int(ok.argmin()); o["lander"] = [q[i]["n"], round(float(ok[i]), 1)]
        d, q = near(p["la"], p["lo"], cands, kla, klo)
        if d is not None:
            ok = d.copy()
            if p["k"].startswith("candidate"): ok[ok < 0.5] = 1e9
            i = int(ok.argmin()); o["cand"] = [q[i]["n"], round(float(ok[i]), 1)]
        if o: v["o"] = o
        out[k] = v
    json.dump(out, open(os.path.join(HERE, "viewer", "point_values.json"), "w"), separators=(",", ":"))
    print("wrote", len(out), "locations")
