The 8 dimensions they score on:
Geology, mineralogy, surface materials
Terrain: elevation, slope, roughness, craters
Temperature, illumination, environmental extremes
Water, ice, permafrost, resources
Dust, wind, erosion, aeolian processes
Biology, extremophiles, habitability, biosignatures
Caves, lava tubes, subsurface
Ops: landing, mobility, navigation, robotics, construction, human factors

Hard constraints stated in the brief: Earth can't reproduce lunar gravity, vacuum, Martian atmosphere or radiation — you're expected to name that failure explicitly. And Atacama / Antarctica / Iceland / Hawaii / Mojave / Death Valley / Haughton are named as "already done" — re-discovering them scores badly.
The databases that already exist

USGS — Known Terrestrial Analog Sites for Planetary Science ← this is the database
DOI 10.5066/P9J72921 (Hunter, 2020), CC0. I downloaded and parsed the shapefile: 192 points. Fields are just Name, AnalogType, Lat, Lon, AnalogBody — and it's 190 impact craters, 1 dune field, 1 volcanic site, with AnalogBody blank on 191 of 192. It's a crater list, not an analog database. (The live ArcGIS feature service currently only serves 4 features — use the shapefile release, not the service.)

USGS TADP — tadp.astrogeology.usgs.gov, the intended permanent analog repository. First ingestion is PAAD (Planetary Aeolian Analog Database), DOI 10.5066/P9IFVZEX: 45 dune fields worldwide with bedforms, climate class, sand source/composition, elevation, areal coverage.

ESA Catalogue of Planetary Analogues (2012, Preston/Grady/Barber, Open University, ESA contract 4000104716) — ~30 site chapters with coordinates and full dossiers, cross-indexed by feature: lunar craters/ejecta/melt/regolith/volcanic pits/rilles/anorthosite/basalt, Martian gullies/lava tubes/mud volcanoes/deltas/yardangs/TARs/dust devils. PDF on esamultimedia.esa.int. Old but the richest per-feature taxonomy.

NASA Planetary Analog Explorer — ~11 curated Earth↔other-world image pairs (Kīlauea/Moon, Death Valley/Mars, Atacama/Mars, Iceland/Moon, Lake Salda/Mars, Aden Crater/Venus). Public-facing, no data.
PANGAEA mineralogical database (ESA EAC) — analog minerals + Raman/VNIR spectral library.

Mars Society stations (MDRS Utah, FMARS Devon Island) — operational analogs, not geospatial data.

The hole: USGS's own 2024 community survey (OFR 2024-1042) states plainly — "a central repository for terrestrial analog field data does not exist." 84% of respondents said they'd use one. That's the gap this challenge is designed to make you fill.

Official data stack (from the Resources tab)

Earth: NASA Earthdata Search, NASA Worldview
Moon/Mars: NASA PDS, LRO (LROC, LOLA, Diviner, LEND, Mini-RF) + Diviner polar temperature products
Partners: CSA RADARSAT-1 + RCM (+ their SAR Python/QGIS tutorial), ESA Copernicus Data Space + Open Science Catalog, JAXA G-Portal