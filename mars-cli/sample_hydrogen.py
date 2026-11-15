#!/usr/bin/env python3
"""Add Odyssey Neutron Spectrometer epithermal neutron flux (NASA PDS, Feldman+ 2002) to viewer/point_values.json.
Source: https://pds-geosciences.wustl.edu/ody/urn-nasa-pds-odyssey_grs_special/data/ns_epithermal_020917.tab
0.5 x 0.5 degree bins, counts/second, first 25.7 days of mapping. This is a RAW neutron count rate, not water %:
fewer epithermal neutrons = more hydrogen (likely water ice) in the top ~1 m."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
tab = sys.argv[1]
a = np.loadtxt(tab, delimiter=",")
G = np.zeros((360, 720))
for lon, lat, v in a:
    G[int((lat + 90) // 0.5), int((lon % 360) // 0.5)] = v
ok = G[G > 0]
print("bins with data:", ok.size, "of", G.size, "min/median/max", ok.min(), np.median(ok), ok.max())
srt = np.sort(ok)
p = os.path.join(HERE, "viewer", "point_values.json")
pv = json.load(open(p)); n = 0
for k in pv:
    la, lo = map(float, k.split(","))
    v = G[min(359, int((la + 90) // 0.5)), int((lo % 360) // 0.5)]
    if v > 0:
        pv[k]["h"] = {"v": round(float(v), 2), "pct": int(round(100 * np.searchsorted(srt, v) / srt.size))}; n += 1
json.dump(pv, open(p, "w"), separators=(",", ":"))
print("added at", n, "of", len(pv))
for k in ["18.4400,77.4500","-4.5900,137.4400","21.6900,78.8500","-8.3500,239.9000"]: print(k, pv[k].get("h"))
