# Moon data CLI prototype

Local data CLI and extraction prototype. Requires
Node.js with built-in fetch (tested with the installed Node). No packages needed.
Use `--use-system-ca` on this computer so Node trusts the installed certificate authorities.

From the repository root:

```powershell
node --use-system-ca moon-cli/moon.mjs datasets
node --use-system-ca moon-cli/moon.mjs sites
node --use-system-ca moon-cli/moon.mjs site copernicus
node moon-cli/moon.mjs dimensions
node moon-cli/moon.mjs measurements copernicus
node moon-cli/moon.mjs analogs
node --use-system-ca moon-cli/moon.mjs sample 9.625 339.925
```

Read commands use local JSON and need no NASA query. `sample LAT LON_E [SITE_ID]`
retrieves a LOLA sample, then saves it under `data/samples/ROW_COL.json` and
registers or updates a local site record. Use a stable site ID to update the same
site on later samples. Sampling the same pixel replaces its saved sample.
Latitude is planetocentric degrees; longitude is east-positive and wraps at 360.
Requested and sampled pixel-center coordinates are both preserved.

## Implemented and live-tested

- Locally queryable eight scoring dimensions and every supplied subdimension.
- Locally queryable site, dataset, measurement, and analog-source records.
- The explicit Earth physical mismatch constraints: lunar gravity and vacuum,
  Martian atmosphere, and radiation cannot be reproduced fully on Earth.
- Named already-done analog examples to prevent presenting them as new discoveries.
- Copernicus site imported from the existing report, and its measured terrain
  sample registered in the local site database.
- Official PDS LOLA `LDEM_16_FLOAT` label validation and exact HTTP range reads.
  Five complete rows (~115 KB) are read instead of the ~66 MB global image.
  A server ignoring range requests is rejected before reading its full body.
- Pixel elevation in meters relative to the 1737.4 km reference sphere (not geoid).
- Plane-fit slope, RMS residual roughness, and maximum-minus-minimum relief
  over a 5 by 5 pixel window. Physical spacing uses the lunar reference radius
  and cosine latitude correction. The raw elevation window is saved for auditing.
- Each measurement records units, source product, method, spatial scale, and
  quality notes. The original source label and retrieval timestamp are retained.

The source label documents little-endian 32-bit floats in kilometers, with
height = DN times scaling factor; its OFFSET is for converting height to
planetary radius and must NOT be added to the height measurement.

## Limits and remaining work

This is a first working data layer, not full Mars feature parity. Map spacing is
about 1.895 km north-south and smaller east-west away from the equator. Window
width is about 9.5 km north-south. These are regional terrain statistics, not
meter-scale hazards or site-wide crater averages. The map contains interpolation;
the prototype checks finite values and conservative elevation bounds, but has no
independent per-pixel observation-count mask. Latitude outside -85..85 is rejected;
polar study sites require a projected polar DEM adapter.

The eight category groups and 27 subdimensions are represented. Unimplemented
measurements remain null with a status; they are not treated as a zero or score.
No temperature, rock abundance, mineral map, illumination, hydrogen, cave catalog,
mission catalog, or operational scoring adapter is implemented yet. Wind is marked
not applicable. Copernicus bounds and feature class come from the prior saved
report, not a fresh live feature lookup. Additional site facts need source review.
`ready_for_scoring` remains false. The included analog registry documents the
known sources and their limitations; it does not claim that those catalogs have
been ingested as a complete collection of Earth site measurements. The USGS
shapefile summary and repository gap are retained as challenge context.

Next adapters can follow this same output contract: select a documented product,
validate label units/projection/scaling, sample valid pixels, preserve spatial and
temporal context, and save provenance. Temperature needs explicit local time and
season. Hydrogen proxies must not be labeled as direct ice measurements.

Source: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/float_img/ldem_16_float.lbl
