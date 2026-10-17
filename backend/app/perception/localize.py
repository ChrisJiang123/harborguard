"""Anonymous positive-ray triangulation and spatial clustering."""
from __future__ import annotations

import math
from collections import Counter
from itertools import combinations

import numpy as np

from .. import config
from ..geo import to_local


def localize(observations: list[dict], buoys: dict | list) -> list[dict]:
    """Return {x,y,depth,covariance,cue} measurements, with no truth IDs.

    Bearing is clockwise from north; positive elevation points down. Independent
    bearing variances are propagated through the intersection Jacobian.
    """
    buoy_map = buoys if isinstance(buoys, dict) else {b["id"]: b for b in buoys}
    usable = []
    for obs in observations:
        buoy = buoy_map.get(obs["buoy_id"])
        if buoy is None or buoy.get("status", "ok") != "ok":
            continue
        # Isolated low-SNR virtual false alarms must not manufacture positions.
        if obs.get("snr_db", config.DT_DB + 1) <= config.DT_DB:
            continue
        b = math.radians(obs["bearing_deg"])
        usable.append((obs, buoy, np.array(to_local(buoy["lat"], buoy["lon"])), np.array([math.sin(b), math.cos(b)])))
    intersections = []
    for i, j in combinations(range(len(usable)), 2):
        oa, ba, pa, da = usable[i]
        ob, bb, pb, db = usable[j]
        if oa["buoy_id"] == ob["buoy_id"] or oa.get("cue", "none") != ob.get("cue", "none"):
            continue
        # Acute crossing angle, so almost antiparallel rays are also rejected.
        cross = float(da[0] * db[1] - da[1] * db[0])
        angle = math.degrees(math.asin(min(1.0, abs(cross))))
        if angle <= config.MIN_INTERSECTION_ANGLE_DEG:
            continue
        ranges = np.linalg.solve(np.column_stack((da, -db)), pb - pa)
        if any(r <= 0 or r > config.LOCALIZE_RANGE_FACTOR * b.get("range_m", 600) for r, b in zip(ranges, (ba, bb), strict=True)):
            continue
        # Anonymous acoustic level disambiguates cross-pairs when several
        # broadband sources are audible. Consider every source-level hypothesis
        # for the observed cue; never consult a target class or identity.
        consistent = True
        range_score = 0.0
        for distance, observation in zip(ranges, (oa, ob), strict=True):
            if "noise_level_db" not in observation:
                continue
            possible_classes = {"narrowband": ("uuv",), "call": ("marine_mammal",),
                                "broadband": ("vessel", "fish_school")}.get(observation.get("cue"), ())
            errors = []
            for cls in possible_classes:
                acoustic_range = 10 ** ((config.SL_DB[cls] - observation["noise_level_db"] - observation["snr_db"]) / 20)
                sigma = math.radians(observation.get("bearing_sigma_deg", config.BEARING_BASE_SIGMA_DEG))
                tolerance = max(config.LOCALIZE_SNR_RANGE_MIN_TOL_M,
                                config.LOCALIZE_SNR_RANGE_SIGMA_GATE * acoustic_range * sigma / abs(cross))
                errors.append(abs(distance - acoustic_range) / tolerance)
            if errors:
                range_score += min(errors)
                consistent = consistent and min(errors) <= 1
        if not consistent:
            continue
        p = pa + ranges[0] * da
        depths = [r * math.tan(math.radians(o.get("elevation_deg", 0))) for r, o in zip(ranges, (oa, ob), strict=True)]
        # Rows are normals to each bearing. Covariance accounts for intersection angle.
        normals = np.array([[da[1], -da[0]], [db[1], -db[0]]])
        sigmas = [r * math.radians(o.get("bearing_sigma_deg", config.BEARING_BASE_SIGMA_DEG)) for r, o in zip(ranges, (oa, ob), strict=True)]
        inverse = np.linalg.inv(normals)
        covariance = inverse @ np.diag(np.square(sigmas)) @ inverse.T
        values, vectors = np.linalg.eigh(covariance)
        covariance = vectors @ np.diag(np.clip(values, config.PERCEPTION_MIN_VARIANCE_M2, config.PERCEPTION_MAX_VARIANCE_M2)) @ vectors.T
        intersections.append({"position": p, "depth": float(np.clip(np.mean(depths), 0, config.SEABED_DEPTH_M)),
                              "covariance": covariance, "cue": oa.get("cue", "none"), "observations": {i, j}, "range_score": range_score})
    # Dense hypotheses go first, which prevents a distant accidental pair from
    # pulling a well-supported intersection cluster out of position.
    if intersections:
        positions = np.asarray([item["position"] for item in intersections])
        distances_squared = np.sum((positions[:, None] - positions[None, :]) ** 2, axis=2)
        cues = np.asarray([item["cue"] for item in intersections])
        density = np.sum((distances_squared <= config.CLUSTER_RADIUS_M ** 2) & (cues[:, None] == cues[None, :]), axis=1)
        intersections = [intersections[index] for index in np.argsort(-density, kind="stable")]
    clusters = []
    for candidate in intersections:
        cluster = next((c for c in clusters if c[0]["cue"] == candidate["cue"] and np.linalg.norm(candidate["position"] - np.mean([p["position"] for p in c], axis=0)) <= config.CLUSTER_RADIUS_M), None)
        if cluster is None:
            clusters.append([candidate])
        else:
            cluster.append(candidate)
    measurements = []
    used = set()
    for cluster in sorted(clusters, key=lambda c: (-len(set.union(*(p["observations"] for p in c))), np.mean([p["range_score"] for p in c]))):
        ids = set.union(*(p["observations"] for p in cluster))
        if len(ids - used) < 2:
            continue
        used.update(ids)
        p = np.mean([c["position"] for c in cluster], axis=0)
        cov = np.zeros((3, 3))
        # Pair intersections are correlated because they share bearings. Do not
        # divide covariance by pair count and claim false extra precision.
        cov[:2, :2] = np.mean([c["covariance"] for c in cluster], axis=0)
        cov[2, 2] = config.PERCEPTION_MIN_VARIANCE_M2
        measurements.append({"x": float(p[0]), "y": float(p[1]), "depth": float(np.mean([c["depth"] for c in cluster])),
                             "covariance": cov, "cue": Counter(c["cue"] for c in cluster).most_common(1)[0][0]})
    return measurements
