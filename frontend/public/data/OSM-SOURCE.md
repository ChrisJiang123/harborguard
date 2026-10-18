# Port of Los Angeles Local Context Map Provenance

- Source: © OpenStreetMap contributors, Overpass API.
- License: [Open Database License 1.0 / OSM attribution](https://www.openstreetmap.org/copyright). This is a filtered and coordinate-converted OSM extract; retain attribution and ODbL notices when distributing.
- Extracted: 2026-10-17T06:17:27.416Z.
- OSM data timestamp: 2026-10-17T06:16:02Z.
- Query bounds: south 33.705, west -118.29, north 33.765, east -118.215. Neighboring points may remain beyond the geometry edges to preserve line continuity.
- 407 line features: 62 coastline, 76 roads, 244 piers, 25 breakwaters.
- harbor-osm.geojson retains OSM way IDs, extraction time, query, and license for traceability.

This used one bounded vector query, without downloading OSM raster tiles. Refresh with scripts/fetch-osm.mjs (`npm.cmd run refresh:osm`); do not run frequently. The script writes only after a successful response containing coastline. Update these timestamps/counts after re-extraction.

References: [Overpass bounded geometry](https://dev.overpass-api.de/overpass-doc/en/full_data/bbox.html), [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/).

This small line map is not a complete offline map or navigation product. Business zones, security assets, buoy coordinates, and simulated reopening policies are not results of this OSM extraction.
