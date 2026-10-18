# Port of Los Angeles Building Footprint Provenance

- Source: Los Angeles County GISNET Public, MapServer layer 434, **Building Outline (2023)**.
- Service: <https://rpgis.isd.lacounty.gov/arcgis/rest/services/GISNET_Public/MapServer/434>.
- Listed copyright holders: LARIAC, County of Los Angeles, Pictometry, EagleView.
- Terms: County of Los Angeles eGIS custom terms, <https://egis-lacounty.hub.arcgis.com/pages/terms-of-use>. Attribution, dates, and copyright holders are retained. Confirm redistribution rights under those custom terms before publicly redistributing this dataset.
- The service describes footprints, heights, areas, and roof elevation derived from imagery. Its metadata mention both 2017 LARIAC5 acquisition and the Building Outline (2023) layer name. Do not describe this as a newly flown 2023 survey; source date descriptions differ.
- Native CRS: EPSG:2229 (NAD83 / California zone 5, US survey feet). The service transforms output geometry to EPSG:4326 in degrees. HEIGHT retains source feet and converts to scene meters using 1 US survey foot = 1200/3937 m.
- ELEV is roof elevation, but its vertical datum could not be confirmed. A does not use it to position building bases. White models rise from the scene reference plane; absolute ground elevation remains untied to water/seabed datums.
- Bounds: west -118.31, south 33.70, east -118.19, north 33.765, covering the demo DEM. Shape.STArea() > 10000 square feet selects larger buildings to reduce mesh/GPU load.
- Packaged snapshot: 487 valid footprints, all with positive HEIGHT. Features retain County OBJECTID, original feet, converted meters, and update status.
- Refresh from frontend/ with `npm.cmd run refresh:buildings`. The script writes only after successful queries with valid Polygon geometry and height. The file is a static service snapshot; browsers do not query County servers at runtime.

Footprints/heights come from actual County GIS, but this is not full 3D roof geometry, interiors, live construction status, or ground elevation fit for navigation/emergency decisions.
