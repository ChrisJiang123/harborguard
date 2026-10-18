# HarborGuard Demonstration Data

These are **manually constructed schematic data** in the Port of Los Angeles coordinate region, not verified charts, actual terminal boundaries, channels, buoy deployments, assets, or schedules. Simplified water polygons/adjacency support algorithm and interface demonstrations during a 24-hour hackathon. Do not use them for navigation, real port closure, or safety decisions. They have not been checked vertex-by-vertex against geojson.io imagery; taskbook B2 real-boundary and visual land/water checks remain a team action.

- zones.geojson: 12 valid polygons: 6 berth areas, 4 connected channel segments, 2 anchorages. Adjacency is bidirectional; the entrance reaches every berth.
- assets.json: 5 fictional protected assets inside their schematic berth areas.
- buoys.json: 10 fictional B1–B10 buoys, all inside schematic water. Staggered placement avoids consecutive bearing-intersection angles below 20°; berths have denser coverage. This is not a real uniform 500–800 m deployment.
- vessels.json: 40 fixed fictional schedules within 0–6 hours of scenario start.
- scenarios/scenario_a.yaml: seed 42; one UUV, two fish schools, three cooperative vessels, one distant mammal. The UUV first travels 410 m east, then approaches the container asset to provide an alert-escalation demo sequence.
- scenarios/scenario_b.yaml: seed 7; four seabed debris objects; B4/B7 fail at simulation second 60. Southern routes/container berth can reopen first, with northern areas unsurveyed.

Coordinates use frozen WGS84/local conversion with origin (33.7300, -118.2600). Vessel/asset names are fictional; acoustic, motion, and coverage parameters are demo assumptions.

`python data/build_demo_data.py` rebuilds these files and synchronizes four JSON/GeoJSON files to frontend/public/data/. Afterwards run `python -m pytest backend/tests/test_data.py backend/tests/test_simulation.py`. The generator handles B-owned data and does not create or modify frontend source.
