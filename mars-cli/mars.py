#!/usr/bin/env python3
"""mars.py - Mars-only CLI for the NASA Space Apps analog-site project.

Pure standard library. Commands:
  time      Mars time for an Earth UTC instant (Mars Year, Ls, MSD, local time)
  match     Earth dates in given years with the same solar longitude (season match)
  year      Start/end dates of a Mars Year (Ls 0 to Ls 0)
  sites     List Mars sites in mars_data.json
  site ID   Facts for one site, grouped by dimension
  datasets  List Mars datasets (filter with --dim N)
  selftest  Check the time maths against known landing dates

Time model: Allison & McEwen (2000) / NASA GISS Mars24 algorithm.
Accuracy: Ls to about 0.01-0.1 deg, enough for season matching (not for ops).
Add --json to any command for machine-readable output.
"""
import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "mars_data.json")

SOL_RATIO = 1.0274912517          # Mars sol length in Earth days
MARS_YEAR_DAYS = 686.9726         # mean tropical Mars year, Earth days
MY1_START_JD = 2435208.5          # approx Ls=0 at start of Mars Year 1 (1955-04-11)

# TAI-UTC step table (effective date, seconds)
LEAPS = [
    ((1972, 1, 1), 10), ((1972, 7, 1), 11), ((1973, 1, 1), 12), ((1974, 1, 1), 13),
    ((1975, 1, 1), 14), ((1976, 1, 1), 15), ((1977, 1, 1), 16), ((1978, 1, 1), 17),
    ((1979, 1, 1), 18), ((1980, 1, 1), 19), ((1981, 7, 1), 20), ((1982, 7, 1), 21),
    ((1983, 7, 1), 22), ((1985, 7, 1), 23), ((1988, 1, 1), 24), ((1990, 1, 1), 25),
    ((1991, 1, 1), 26), ((1992, 7, 1), 27), ((1993, 7, 1), 28), ((1994, 7, 1), 29),
    ((1996, 1, 1), 30), ((1997, 7, 1), 31), ((1999, 1, 1), 32), ((2006, 1, 1), 33),
    ((2009, 1, 1), 34), ((2012, 7, 1), 35), ((2015, 7, 1), 36), ((2017, 1, 1), 37),
]

# ---------------------------------------------------------------- time maths

def tai_minus_utc(dt):
    sec = 10
    for (y, m, d), s in LEAPS:
        if dt >= datetime(y, m, d, tzinfo=timezone.utc):
            sec = s
    return sec


def to_jd_utc(dt):
    return dt.timestamp() / 86400.0 + 2440587.5


def jd_tt(dt):
    return to_jd_utc(dt) + (tai_minus_utc(dt) + 32.184) / 86400.0


def from_jd_utc(jd):
    return datetime.fromtimestamp((jd - 2440587.5) * 86400.0, tz=timezone.utc)


def parse_utc(s):
    if s is None or s.lower() == "now":
        return datetime.now(timezone.utc)
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        sys.exit("Could not parse '%s'. Use ISO format, e.g. 2012-08-06T05:17:57 or 2026-11-14." % s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def rad(x):
    return math.radians(x)


def ls_from_jdtt(jdt):
    """Areocentric solar longitude (deg) and equation-of-time pieces."""
    dt = jdt - 2451545.0
    M = (19.3871 + 0.52402073 * dt) % 360.0
    afms = (270.3871 + 0.524038496 * dt) % 360.0
    A = (0.0071, 0.0057, 0.0039, 0.0037, 0.0021, 0.0020, 0.0018)
    tau = (2.2353, 2.7543, 1.1177, 15.7866, 2.1354, 2.4694, 32.8493)
    phi = (49.409, 168.173, 191.837, 21.736, 15.704, 95.528, 49.095)
    pbs = sum(a * math.cos(rad(0.985626 * dt / t + p)) for a, t, p in zip(A, tau, phi))
    eoc = ((10.691 + 3.0e-7 * dt) * math.sin(rad(M)) + 0.623 * math.sin(rad(2 * M))
           + 0.050 * math.sin(rad(3 * M)) + 0.005 * math.sin(rad(4 * M))
           + 0.0005 * math.sin(rad(5 * M)) + pbs)
    ls = (afms + eoc) % 360.0
    eot_deg = (2.861 * math.sin(rad(2 * ls)) - 0.071 * math.sin(rad(4 * ls))
               + 0.002 * math.sin(rad(6 * ls)) - eoc)
    return ls, eot_deg / 15.0  # EOT in hours


def msd_from_jdtt(jdt):
    return (jdt - 2451549.5) / SOL_RATIO + 44796.0 - 0.00096


def mars_year(jdt, ls):
    est = (jdt - MY1_START_JD) / MARS_YEAR_DAYS - ls / 360.0
    return int(round(est)) + 1


def season(ls):
    if ls < 90:
        return "northern spring / southern autumn"
    if ls < 180:
        return "northern summer / southern winter"
    if ls < 270:
        return "northern autumn / southern spring"
    return "northern winter / southern summer"


def hms(hours):
    hours %= 24.0
    s = int(round(hours * 3600)) % 86400
    return "%02d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def mars_time(dt, lon_e=0.0):
    jdt = jd_tt(dt)
    ls, eot_h = ls_from_jdtt(jdt)
    msd = msd_from_jdtt(jdt)
    mtc = 24.0 * (msd % 1.0)
    lmst = mtc + lon_e / 15.0           # east longitude: later local time
    ltst = lmst + eot_h
    return {
        "utc": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "jd_tt": round(jdt, 6),
        "mars_year": mars_year(jdt, ls),
        "ls_deg": round(ls, 3),
        "season": season(ls),
        "msd": round(msd, 5),
        "mtc_airy": hms(mtc),
        "lon_east_deg": lon_e,
        "lmst": hms(lmst),
        "ltst": hms(ltst),
        "eot_min": round(eot_h * 60, 2),
    }


def angdiff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def ls_zero_jd(my):
    """JD (UTC-ish, TT treated ~UTC to ~1 min) when Mars Year `my` begins (Ls 0)."""
    jd = MY1_START_JD + (my - 1) * MARS_YEAR_DAYS
    for _ in range(30):
        ls, _e = ls_from_jdtt(jd)
        err = angdiff(ls, 0.0)
        jd -= err / 360.0 * MARS_YEAR_DAYS
        if abs(err) < 1e-6:
            break
    return jd - (69.184 / 86400.0)


# -------------------------------------------------------------- Earth season

def earth_sun_lon(jd):
    n = jd - 2451545.0
    L = 280.460 + 0.9856474 * n
    g = rad(357.528 + 0.9856003 * n)
    return (L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360.0


def earth_date_for_ls(year, ls):
    """Earth UTC instant in `year` when the Sun's longitude equals `ls`."""
    jd = to_jd_utc(datetime(year, 3, 20, tzinfo=timezone.utc)) + ls / 360.0 * 365.2422
    for _ in range(30):
        err = angdiff(earth_sun_lon(jd), ls)
        jd -= err / 0.9856474
        if abs(err) < 1e-6:
            break
    return from_jd_utc(jd)


def earth_time_for_local(dt_date, ltst_hours, earth_lon_e):
    """UTC instant on dt_date's day where Earth mean local time = ltst_hours."""
    utc_hours = (ltst_hours - earth_lon_e / 15.0) % 24.0
    base = datetime(dt_date.year, dt_date.month, dt_date.day, tzinfo=timezone.utc)
    return base + timedelta(hours=utc_hours)


def parse_hhmm(s):
    try:
        h, m = s.split(":")[:2]
        return int(h) + int(m) / 60.0
    except Exception:
        sys.exit("Bad time '%s'. Use HH:MM, e.g. 14:30." % s)


# ------------------------------------------------------------------- output

def emit(obj, as_json, text_fn):
    if as_json:
        print(json.dumps(obj, indent=2, default=str))
    else:
        text_fn(obj)


def load_data():
    if not os.path.exists(DATA_FILE):
        sys.exit("mars_data.json not found next to mars.py (%s)." % DATA_FILE)
    with open(DATA_FILE) as f:
        return json.load(f)


# ----------------------------------------------------------------- commands

def cmd_time(a):
    dt = parse_utc(a.utc)
    r = mars_time(dt, a.lon)

    def show(r):
        print("Earth UTC      %s" % r["utc"])
        print("Mars Year      MY%d" % r["mars_year"])
        print("Ls             %.3f deg  (%s)" % (r["ls_deg"], r["season"]))
        print("Mars Sol Date  %.5f" % r["msd"])
        print("Mean time Airy %s (MTC)" % r["mtc_airy"])
        print("Local time     %s mean / %s true solar, at %.2f E" % (r["lmst"], r["ltst"], r["lon_east_deg"]))
        print("Eq. of time    %+.2f min" % r["eot_min"])
    emit(r, a.json, show)


def cmd_match(a):
    if a.ls is not None:
        ls = a.ls % 360.0
        src = {"ls_deg": ls}
        ltst = None
    else:
        r = mars_time(parse_utc(a.utc), a.lon)
        ls = r["ls_deg"]
        src = r
        ltst = parse_hhmm(r["ltst"][:5])
    if a.ltst:
        ltst = parse_hhmm(a.ltst)
    rows = []
    for y in a.years:
        d = earth_date_for_ls(y, ls)
        row = {"year": y, "earth_date_utc": d.strftime("%Y-%m-%d"), "earth_ls_check": round(earth_sun_lon(to_jd_utc(d)), 2)}
        if ltst is not None:
            t = earth_time_for_local(d, ltst, a.earth_lon)
            row["utc_for_same_local_time"] = t.strftime("%Y-%m-%dT%H:%MZ")
        rows.append(row)
    out = {"mars_ls_deg": round(ls, 3), "matched_local_time": hms(ltst) if ltst is not None else None,
           "earth_lon_east": a.earth_lon, "matches": rows}

    def show(o):
        print("Mars Ls %.3f deg -> Earth dates with the same Sun longitude" % o["mars_ls_deg"])
        if o["matched_local_time"]:
            print("Local solar time %s at Earth lon %.2f E" % (o["matched_local_time"], o["earth_lon_east"]))
        for r in o["matches"]:
            extra = "  UTC %s" % r["utc_for_same_local_time"] if "utc_for_same_local_time" in r else ""
            print("  %d  %s%s" % (r["year"], r["earth_date_utc"], extra))
    emit(out, a.json, show)


def cmd_year(a):
    s = ls_zero_jd(a.my)
    e = ls_zero_jd(a.my + 1)
    out = {"mars_year": a.my, "start_utc": from_jd_utc(s).strftime("%Y-%m-%d %H:%M"),
           "end_utc": from_jd_utc(e).strftime("%Y-%m-%d %H:%M"), "length_days": round(e - s, 2),
           "length_sols": round((e - s) / SOL_RATIO, 1)}
    rows = []
    for L in (0, 90, 180, 270):
        j = s + (ls_zero_jd_target(a.my, L) - s)
        rows.append({"ls": L, "utc": from_jd_utc(j).strftime("%Y-%m-%d")})
    out["quarters"] = rows

    def show(o):
        print("MY%d: %s to %s" % (o["mars_year"], o["start_utc"], o["end_utc"]))
        print("Length: %.2f Earth days = %.1f sols" % (o["length_days"], o["length_sols"]))
        for r in o["quarters"]:
            print("  Ls %3d  %s" % (r["ls"], r["utc"]))
    emit(out, a.json, show)


def ls_zero_jd_target(my, target):
    jd = ls_zero_jd(my) + target / 360.0 * MARS_YEAR_DAYS
    for _ in range(40):
        ls, _e = ls_from_jdtt(jd + 69.184 / 86400.0)
        err = angdiff(ls, target)
        jd -= err / 360.0 * MARS_YEAR_DAYS
        if abs(err) < 1e-6:
            break
    return jd


def cmd_sites(a):
    d = load_data()
    rows = [{"id": s["id"], "name": s["name"], "lat": s["lat"], "lon_e": s["lon_e"], "facts": len(s["facts"])} for s in d["sites"]]

    def show(r):
        for s in r:
            print("%-9s %-24s lat %6.2f  lon_E %7.2f  %2d facts" % (s["id"], s["name"], s["lat"], s["lon_e"], s["facts"]))
        print("\nCoordinates are approximate - check the USGS gazetteer.")
    emit(rows, a.json, show)


def fmt_val(f):
    v = f.get("value")
    if v is None:
        return "(no value)"
    if isinstance(v, list):
        v = " to ".join(str(x) for x in v)
    unit = f.get("unit")
    return "%s %s" % (v, unit) if unit else str(v)


def cmd_site(a):
    d = load_data()
    site = next((s for s in d["sites"] if s["id"] == a.id.lower()), None)
    if site is None:
        sys.exit("No site '%s'. Try: %s" % (a.id, ", ".join(s["id"] for s in d["sites"])))
    if a.json:
        print(json.dumps(site, indent=2))
        return
    print("%s  (lat %.2f, lon %.2f E)" % (site["name"], site["lat"], site["lon_e"]))
    names = d["dimensions"]
    by_dim = {}
    for f in site["facts"]:
        by_dim.setdefault(f["dim"], []).append(f)
    for dim in sorted(by_dim):
        print("\n[%d] %s" % (dim, names[str(dim)]))
        for f in by_dim[dim]:
            tag = "" if f["status"] == "sourced" else "  <%s>" % f["status"].upper()
            print("  - %s: %s%s" % (f["key"], fmt_val(f), tag))
            if f.get("note"):
                print("      note: %s" % f["note"])
    print("\nStatus tags: UNVERIFIED = no published number found, WEAK_SOURCE = Wikipedia only.")


def cmd_datasets(a):
    d = load_data()
    rows = [x for x in d["datasets"] if a.dim is None or a.dim in x["dims"]]

    def show(r):
        for x in r:
            print("%-16s %s" % (x["id"], x["name"]))
            print("   dims %s | %s | %s | %s" % (x["dims"], x["coverage"], x["resolution"], x["time_type"]))
            print("   %s" % x["url"])
        print("\n%d dataset(s)." % len(r))
    emit(rows, a.json, show)


def cmd_cite(a):
    path = os.path.join(HERE, "mars_citations.json")
    with open(path) as f:
        c = json.load(f)
    dims = c["dims"]
    names = load_data()["dimensions"]
    print(c["note"] + "\n")
    for k in sorted(dims, key=int):
        if a.dim is not None and int(k) != a.dim:
            continue
        print("Dimension %s: %s" % (k, names.get(k, "")))
        for x in dims[k]:
            print("  - %s [%s]\n    %s\n    %s\n    %s" % (x["data"], x["status"], x["source"], x["cite"], x["url"]))
        print()


def load_features():
    path = os.path.join(HERE, "mars_features.json")
    if not os.path.exists(path):
        sys.exit("mars_features.json not found next to mars.py.")
    with open(path) as f:
        d = json.load(f)
    seen, out = set(), []
    for x in d["features"]:           # the source shapefile repeats one point (Bohar)
        k = (x["name"], x["lat"], x["lon_e"])
        if k not in seen:
            seen.add(k)
            out.append(x)
    return d, out


def cmd_features(a):
    d, feats = load_features()
    if a.name:
        q = a.name.lower()
        feats = [x for x in feats if q in x["name"].lower()]
    if a.type:
        q = a.type.lower()
        feats = [x for x in feats if q in x["type"].lower()]
    if a.bbox:
        s, n, w, e = a.bbox
        feats = [x for x in feats if x["lat"] is not None and s <= x["lat"] <= n and w <= x["lon_e"] <= e]
    if a.counts:
        c = {}
        for x in feats:
            c[x["type"]] = c.get(x["type"], 0) + 1
        out = {"total": len(feats), "by_type": dict(sorted(c.items(), key=lambda kv: -kv[1]))}

        def show(o):
            print("Total: %d" % o["total"])
            for k, v in o["by_type"].items():
                print("  %5d  %s" % (v, k))
        emit(out, a.json, show)
        return
    shown = feats[: a.limit]

    def show(rows):
        for x in rows:
            dia = "%.1f km" % x["diam_km"] if x["diam_km"] else "-"
            print("%-22s %-22s lat %8.3f lon_E %8.3f  %s" % (x["name"][:22], x["type"][:22], x["lat"], x["lon_e"], dia))
        print("\n%d of %d match (use --limit to see more). Source: USGS Gazetteer." % (len(rows), len(feats)))
    emit(shown, a.json, show)


def load_json(name, key):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        sys.exit("%s not found next to mars.py." % name)
    with open(path) as f:
        d = json.load(f)
    return d, d[key]


def cmd_caves(a):
    d, rows = load_json("mars_caves.json", "caves")
    if a.type:
        rows = [x for x in rows if x["type"].lower() == a.type.lower()]
    if a.priority is not None:
        rows = [x for x in rows if x["priority"] == a.priority]
    if a.bbox:
        s, n, w, e = a.bbox
        rows = [x for x in rows if s <= x["lat"] <= n and w <= x["lon_e"] <= e]
    if a.counts:
        c = {}
        for x in rows:
            c[x["type"]] = c.get(x["type"], 0) + 1
        out = {"total": len(rows), "by_type": dict(sorted(c.items(), key=lambda kv: -kv[1]))}

        def show(o):
            print("Total: %d" % o["total"])
            for k, v in o["by_type"].items():
                print("  %5d  %s" % (v, k))
        emit(out, a.json, show)
        return

    def show(r):
        for x in r:
            print("%-8s %-5s p%d  lat %8.3f lon_E %8.3f  %s" % (x["id"], x["type"], x["priority"], x["lat"], x["lon_e"], x["comment"][:50]))
        print("\n%d shown of %d. Source: USGS MGC3 (Cushing)." % (len(r), len(rows)))
    emit(rows[: a.limit], a.json, show)


def cmd_landers(a):
    d, rows = load_json("mars_landers.json", "landers")

    def show(r):
        for x in r:
            pos = "lat %7.2f lon_E %7.2f" % (x["lat"], x["lon_e"]) if x["lat"] is not None else "no coordinate"
            print("%-24s %s  %-22s %s" % (x["name"], x["date"], pos, x["outcome"]))
        print("\n%d entries. %s" % (len(r), d["source"]))
    emit(rows, a.json, show)


def cmd_candidates(a):
    d, rows = load_json("mars_candidates.json", "candidates")
    if a.group:
        rows = [x for x in rows if a.group.lower() in x["group"].lower()]

    def show(r):
        last = None
        for x in r:
            if x["group"] != last:
                print("\n== %s" % x["group"])
                last = x["group"]
            pos = "lat %8.3f lon_E %8s" % (x["lat"], "%.3f" % x["lon_e"] if x["lon_e"] is not None else "-") if x["lat"] is not None else "no coordinate"
            print("  %-52s %s" % (x["name"][:52], pos))
        print("\n%d entries. Blank = NASA document gives none." % len(r))
    emit(rows, a.json, show)


KEY_FEATURES = {"Olympus Mons", "Arsia Mons", "Pavonis Mons", "Ascraeus Mons", "Elysium Mons",
                "Valles Marineris", "Hellas Planitia", "Argyre Planitia", "Utopia Planitia",
                "Noctis Labyrinthus", "Syrtis Major Planum", "Tharsis Montes"}


def feature_dim(ftype):
    """Map a gazetteer feature type to one of the 8 layers. This mapping is ours, not NASA's."""
    t = ftype.lower()
    if any(k in t for k in ("mons", "tholus", "patera", "planum", "terra", "fluctus")):
        return 1          # volcanic edifices, plateaus, lava flows -> geology / surface materials
    if "chaos" in t:
        return 4          # chaos terrain is linked to water/ice release (interpretive)
    if "unda" in t or "albedo" in t:
        return 5          # dune fields, dust/albedo markings -> aeolian
    return 2              # craters, valleys, scarps, mesas ... -> terrain


def build_viewer_data():
    """Collect every record from the JSON files into viewer/data.js."""
    main = load_data()
    feats_doc, feats = load_features()
    _c, caves = load_json("mars_caves.json", "caves")
    _l, landers = load_json("mars_landers.json", "landers")
    _k, cands = load_json("mars_candidates.json", "candidates")
    pts = []

    for s in main["sites"]:
        dims = sorted({f["dim"] for f in s["facts"] if f.get("value") is not None})
        lines = []
        for f in s["facts"]:
            tag = "" if f["status"] == "sourced" else " [%s]" % f["status"]
            lines.append("D%d %s: %s%s" % (f["dim"], f["key"], fmt_val(f), tag))
        pts.append({"n": s["name"], "k": "researched site", "la": s["lat"], "lo": s["lon_e"], "d": dims or [1],
                    "i": lines, "lab": 1})

    for x in landers:
        if x["lat"] is None:
            continue
        pts.append({"n": x["name"], "k": "lander / rover", "la": x["lat"], "lo": x["lon_e"], "d": [8],
                    "i": [x["date"], x["outcome"]], "lab": 1})

    for x in cands:
        if x["lat"] is None or x["lon_e"] is None:
            continue
        dims = [8] + ([4] if "ice" in x["name"].lower() else [])
        pts.append({"n": x["name"], "k": "candidate / exploration zone", "la": x["lat"], "lo": x["lon_e"], "d": dims,
                    "i": [x["group"], x.get("note", "")], "lab": 1 if "final" in x["group"].lower() else 0})

    for x in caves:
        pts.append({"n": x["id"], "k": "cave candidate (%s)" % x["type"], "la": x["lat"], "lo": x["lon_e"], "d": [7],
                    "i": ["priority %d (0 = HiRISE image exists)" % x["priority"], x["comment"]], "lab": 0})

    for x in feats:
        if x["lat"] is None:
            continue
        info = [x["type"]]
        if x["diam_km"]:
            info.append("%.1f km" % x["diam_km"])
        if x["origin"]:
            info.append(x["origin"])
        pts.append({"n": x["name"], "k": "named feature", "la": round(x["lat"], 4), "lo": round(x["lon_e"], 4),
                    "d": [feature_dim(x["type"])], "i": info, "lab": 1 if x["name"] in KEY_FEATURES else 0})

    # elevation (metres) at each dot, sampled from the NASA MOLA 463 m DEM; file made once from the USGS GeoTIFF
    ep = os.path.join(HERE, "viewer", "elev_samples.json")
    if os.path.exists(ep):
        with open(ep) as f:
            samples = json.load(f)
        for p in pts:
            v = samples.get("%.4f,%.4f" % (p["la"], p["lo"]))
            if v is not None:
                p["el"] = v
    vp = os.path.join(HERE, "viewer", "point_values.json")      # made by sample_values.py from NASA rasters
    if os.path.exists(vp):
        with open(vp) as f:
            vals = json.load(f)
        for p in pts:
            v = vals.get("%.4f,%.4f" % (p["la"], p["lo"]))
            if v:
                p["v"] = v
    cp = os.path.join(HERE, "mars_citations.json")
    cites = json.load(open(cp))["dims"] if os.path.exists(cp) else {}
    ds = [{"n": x["name"], "d": x["dims"], "cov": x["coverage"], "res": x["resolution"], "u": x["url"]}
          for x in main["datasets"] if len(x["dims"]) < 8]
    doc = {"dims": {int(k): v for k, v in main["dimensions"].items()}, "points": pts, "datasets": ds,
           "cites": cites, "texLon0": 0, "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    vdir = os.path.join(HERE, "viewer")
    os.makedirs(vdir, exist_ok=True)
    with open(os.path.join(vdir, "data.js"), "w") as f:
        f.write("window.MARS=")
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
        f.write(";\n")
    counts = {}
    for p in pts:
        for d in p["d"]:
            counts[d] = counts.get(d, 0) + 1
    return len(pts), counts, vdir


def cmd_viewer(a):
    import http.server
    import threading
    import webbrowser
    n, counts, vdir = build_viewer_data()
    print("Built viewer/data.js: %d records." % n)
    for d in sorted(counts):
        print("  layer %d: %5d dots" % (d, counts[d]))
    if a.build_only:
        return
    if not os.path.exists(os.path.join(vdir, "index.html")):
        sys.exit("viewer/index.html is missing.")

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=vdir, **kw)

        def log_message(self, *args):
            pass
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), H)
    except OSError:
        sys.exit("Port %d is busy. Try: python3 mars.py viewer --port 8766" % a.port)
    url = "http://127.0.0.1:%d/" % a.port
    print("Serving %s  (Ctrl+C to stop)" % url)
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def cmd_selftest(a):
    checks = [
        # name, UTC, lon_e, expected Ls, ls tolerance, expected MY
        ("Curiosity landing (Gale)", "2012-08-06T05:17:57", 137.44, 150.7, 0.6, 31),
        ("Perseverance landing (Jezero)", "2021-02-18T20:55:00", 77.45, 5.2, 0.6, 36),
    ]
    ok = True
    for name, utc, lon, ls_exp, tol, my_exp in checks:
        r = mars_time(parse_utc(utc), lon)
        good = abs(angdiff(r["ls_deg"], ls_exp)) <= tol and r["mars_year"] == my_exp
        ok &= good
        print("%s %-30s Ls %.2f (want ~%.1f) MY%d (want %d)" % ("PASS" if good else "FAIL", name, r["ls_deg"], ls_exp, r["mars_year"], my_exp))
    # Earth match must hit the target longitude
    d = earth_date_for_ls(2026, 150.7)
    e = abs(angdiff(earth_sun_lon(to_jd_utc(d)), 150.7))
    good = e < 0.01
    ok &= good
    print("%s Earth season match error %.5f deg" % ("PASS" if good else "FAIL", e))
    # Mars year length
    s, e2 = ls_zero_jd(35), ls_zero_jd(36)
    good = abs((e2 - s) - 686.97) < 1.0
    ok &= good
    print("%s Mars Year length %.2f days (want ~686.97)" % ("PASS" if good else "FAIL", e2 - s))
    # Data file loads
    try:
        dd = load_data()
        print("PASS data file: %d sites, %d datasets" % (len(dd["sites"]), len(dd["datasets"])))
    except SystemExit as ex:
        ok = False
        print("FAIL data file: %s" % ex)
    print("\nAll checks passed." if ok else "\nSome checks FAILED.")
    sys.exit(0 if ok else 1)


def main():
    p = argparse.ArgumentParser(prog="mars", description="Mars-only CLI: time, season matching, sites, datasets.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("time", parents=[common], help="Mars time for an Earth UTC instant")
    t.add_argument("--utc", help="ISO time, default now")
    t.add_argument("--lon", type=float, default=0.0, help="Mars east longitude in deg (default 0)")
    t.set_defaults(fn=cmd_time)

    m = sub.add_parser("match", parents=[common], help="Earth dates with the same solar longitude")
    m.add_argument("--utc", help="take Ls from this Earth instant (default now)")
    m.add_argument("--ls", type=float, help="or give Ls directly")
    m.add_argument("--lon", type=float, default=0.0, help="Mars east longitude for local time")
    m.add_argument("--years", type=int, nargs="+", default=[datetime.now(timezone.utc).year])
    m.add_argument("--ltst", help="match this Mars local solar time HH:MM")
    m.add_argument("--earth-lon", type=float, default=0.0, help="Earth site east longitude (deg)")
    m.set_defaults(fn=cmd_match)

    y = sub.add_parser("year", parents=[common], help="Dates of a Mars Year")
    y.add_argument("my", type=int)
    y.set_defaults(fn=cmd_year)

    sub.add_parser("sites", parents=[common], help="list sites").set_defaults(fn=cmd_sites)
    s = sub.add_parser("site", parents=[common], help="facts for one site")
    s.add_argument("id")
    s.set_defaults(fn=cmd_site)
    ds = sub.add_parser("datasets", parents=[common], help="list datasets")
    ds.add_argument("--dim", type=int, choices=range(1, 9))
    ds.set_defaults(fn=cmd_datasets)
    ci = sub.add_parser("cite", parents=[common], help="citations for the data behind each of the 8 dimensions")
    ci.add_argument("--dim", type=int, choices=range(1, 9))
    ci.set_defaults(fn=cmd_cite)
    f = sub.add_parser("features", parents=[common], help="USGS gazetteer: every named Mars feature")
    f.add_argument("--name", help="substring of the name")
    f.add_argument("--type", help="substring of the feature type, e.g. crater, mons, vallis")
    f.add_argument("--bbox", type=float, nargs=4, metavar=("S", "N", "W", "E"), help="lat/lon box, east longitude")
    f.add_argument("--counts", action="store_true", help="count by feature type instead of listing")
    f.add_argument("--limit", type=int, default=25)
    f.set_defaults(fn=cmd_features)
    c = sub.add_parser("caves", parents=[common], help="USGS Mars Global Cave Candidate Catalog")
    c.add_argument("--type", help="type code: sky, srp, APC, crk, pin, flr, pit ...")
    c.add_argument("--priority", type=int, choices=range(0, 4))
    c.add_argument("--bbox", type=float, nargs=4, metavar=("S", "N", "W", "E"))
    c.add_argument("--counts", action="store_true")
    c.add_argument("--limit", type=int, default=25)
    c.set_defaults(fn=cmd_caves)
    cd = sub.add_parser("candidates", parents=[common], help="MSL / Mars 2020 shortlists and human Exploration Zones")
    cd.add_argument("--group", help="substring: MSL, Mars 2020, HLS2")
    cd.set_defaults(fn=cmd_candidates)
    v = sub.add_parser("viewer", parents=[common], help="3D Mars globe in your browser (Three.js)")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--no-open", action="store_true", help="do not open the browser")
    v.add_argument("--build-only", action="store_true", help="only rebuild viewer/data.js")
    v.set_defaults(fn=cmd_viewer)
    sub.add_parser("landers", parents=[common], help="every Mars landing attempt (NASA GISS)").set_defaults(fn=cmd_landers)
    sub.add_parser("selftest", parents=[common], help="check time maths").set_defaults(fn=cmd_selftest)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
