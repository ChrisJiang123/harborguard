# Team Static Data

Copy B-provided assets.json, buoys.json, zones.geojson, and vessels.json here. Without team data, local mocks use explicitly labeled example coordinates and do not claim to be real port data.

harbor-osm.geojson is a separate OSM shoreline/context line map, not business zoning; see OSM-SOURCE.md for provenance and ODbL. sonar-stub.svg is a simulated sonar illustration, not physical sonar or trained-model output. B's JSONL files belong in public/ with locally packaged images, for example public/sonar/det-1.png.

`seabed-fill-regional.json` is a separate NOAA CRM regional model/interpolation layer, not additional H12617 measurements. Its metadata retain native datum/resolution and the unresolved vertical tie. See [current shoreline validation](../../../docs/3d-shoreline-realism/README.md).
