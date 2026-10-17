"""Taskbook WGS84/local approximation for this small harbor demonstration.

Coordinates are east/north meters around ``config.ORIGIN``. This is deliberately
the frozen contract's projection, rather than an alternate map projection.
"""
from math import cos, radians

from . import config


def to_local(lat: float, lon: float) -> tuple[float, float]:
    """Convert WGS84 latitude/longitude to local east/north meters."""
    lat0, lon0 = config.ORIGIN
    return (
        (float(lon) - lon0) * config.METERS_PER_LON_DEG * cos(radians(lat0)),
        (float(lat) - lat0) * config.METERS_PER_LAT_DEG,
    )


def to_geo(x_e: float, y_n: float) -> tuple[float, float]:
    """Convert local east/north meters to WGS84 latitude/longitude."""
    lat0, lon0 = config.ORIGIN
    return (
        lat0 + float(y_n) / config.METERS_PER_LAT_DEG,
        lon0 + float(x_e) / (config.METERS_PER_LON_DEG * cos(radians(lat0))),
    )
