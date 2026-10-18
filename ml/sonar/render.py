"""C1 grayscale forward-looking sector sonar renderer. Frozen section7 signature/return format is
imported by B. Polar canvas:512 range bins x256 beams over [0,max_range_m] and [-fov/2,+fov/2],
bearing0 forward/right positive. Output apex is bottom center and opens upward; maximum
radius=min(size-1,(size/2-1)/sin(fov/2)); outside is black. Shadows extend radially behind targets:
dark uuv/debris, short weak mammal, none for fish. Boxes contain echoes, not shadows. Local
default_rng(seed) leaves global RNG untouched and reproduces pixels.
"""


from __future__ import annotations

import math
from numbers import Integral

import cv2
import numpy as np

# C1 polar canvas resolution:512 range bins x256 beams.
RANGE_BINS = 512
BEAMS = 256

# Frozen classes:0uuv,1fish_school,2debris,3marine_mammal.
CLASS_NAMES: tuple[str, ...] = ("uuv", "fish_school", "debris", "marine_mammal")

_MIN_AREA_PX = 16   # Minimum labeled bbox pixel area; discard smaller boxes.
_BLUR_SIGMA = 0.7   # Taskbook Gaussian blur sigma=0.7.


def _sector_geometry(half_fov: float, size: int) -> tuple[float, float, float]:
    """Shared apex and fitted radius for projection, remapping and annotations."""
    return ((size - 1) / 2.0, float(size - 1),
            min(float(size - 1), (size / 2 - 1) / math.sin(half_fov)))


def _sector_pixel(rr: float, theta: float, half_fov: float, size: int) -> tuple[float, float]:
    cx, cy, r_max_px = _sector_geometry(half_fov, size)
    r_px = rr * r_max_px
    return cx + r_px * math.sin(theta), cy - r_px * math.cos(theta)


def range_bearing_to_pixel(
    range_m: float,
    bearing_deg: float,
    *,
    max_range_m: float = 150.0,
    fov_deg: float = 120.0,
    size: int = 640,
) -> tuple[float, float] | None:
    """Project a target center using the exact ``render_ping`` sector geometry.

    Returns continuous (x, y) pixels: image origin at top left, x rightward,
    y downward; sonar apex at ((size-1)/2, size-1). Bearing is relative to
    sonar heading, in degrees, zero forward/up and positive right. Range and
    max_range_m are metres; fov_deg is the full opening angle in (0, 180).
    Pass the same size, fov_deg and max_range_m used for the rendered image.

    Finite centers outside [0, max_range_m] or [-fov_deg/2, fov_deg/2]
    return None, without clamping or angle wrapping; both edges are included.
    Zero and positive near-field ranges are projected physically, without a
    training-range floor. This is a center projection, not an echo/visibility
    guarantee: background has a near 3% dark band, and footprints may be
    clipped or annotations dropped below 16 pixels of area. render_ping's
    legacy target range floor of 1e-3 m is unchanged; to match such an input
    exactly, explicitly project max(range_m, 1e-3) at the caller.

    Nonfinite inputs, invalid geometry, or a noninteger size / size < 16 raise
    ValueError. Keep float pixels for box association; rounding an exact
    sector-edge point may land on an outside (black) raster pixel.
    """
    if not all(math.isfinite(v) for v in (range_m, bearing_deg, max_range_m, fov_deg)):
        raise ValueError("Range, bearing, max_range_m and fov_deg must be finite")
    if max_range_m <= 0.0 or not 0.0 < fov_deg < 180.0:
        raise ValueError("Require max_range_m > 0 and 0 < fov_deg < 180")
    if isinstance(size, bool) or not isinstance(size, Integral) or size < 16:
        raise ValueError("size must be an integer >= 16")
    if not 0.0 <= range_m <= max_range_m or abs(bearing_deg) > fov_deg / 2.0:
        return None
    return _sector_pixel(range_m / max_range_m, math.radians(bearing_deg),
                         math.radians(fov_deg) / 2.0, size)


def render_ping(
    targets: list[dict],
    *,
    max_range_m: float = 150.0,
    fov_deg: float = 120.0,
    noise: float = 0.3,
    seed: int | None = None,
    size: int = 640,
) -> tuple["np.ndarray", list[dict]]:
    """Each target supplies cls (uuv/fish_school/debris/marine_mammal), range_m, bearing_deg (relative
    to forward, within +/-fov/2), length_m, width_m and aspect_deg. Return (size x size uint8
    grayscale image with bottom-center sector apex, labels=[{cls,bbox:[x1,y1,x2,y2]}] in pixels).
    """
    if not 0.0 < fov_deg < 180.0:
        raise ValueError(f"fov_deg must be in (0, 180), received {fov_deg}")
    if max_range_m <= 0.0:
        raise ValueError(f"max_range_m must be positive, received {max_range_m}")
    if size < 16:
        raise ValueError(f"size is too small: {size}")

    rng = np.random.default_rng(seed)  # Local generator leaves global RNG untouched.
    half_fov = math.radians(fov_deg) / 2.0
    fov_rad = 2.0 * half_fov

    canvas = _background(rng, noise)

    echo_extents: list[tuple[str, float, float, float, float]] = []
    # Far range bin, beam bounds, shadow length in bins, intensity.
    shadow_specs: list[tuple[float, float, float, float, float]] = []

    for t in targets:
        cls = str(t["cls"])
        if cls not in CLASS_NAMES:
            raise ValueError(f"Unknown class {cls!r}; allowed: {CLASS_NAMES}")
        rng_m = max(float(t["range_m"]), 1e-3)
        theta = math.radians(float(t["bearing_deg"]))
        length_m = max(float(t["length_m"]), 0.1)
        width_m = max(float(t["width_m"]), 0.1)
        aspect = math.radians(float(t["aspect_deg"]))

        m_per_rbin = max_range_m / RANGE_BINS
        m_per_beam = rng_m * fov_rad / BEAMS          # Transverse meters per beam at this range.
        r_c = rng_m / max_range_m * (RANGE_BINS - 1)  # Target-center range bin.
        b_c = (theta + half_fov) / fov_rad * (BEAMS - 1)

        if cls == "fish_school":
            echo_extents.append(
                (cls, *_scatter_fish(rng, canvas, r_c, b_c, m_per_rbin, m_per_beam))
            )
            continue

        # Radial/transverse size is the target projection along each axis.
        radial_m = length_m * abs(math.cos(aspect)) + width_m * abs(math.sin(aspect))
        tang_m = length_m * abs(math.sin(aspect)) + width_m * abs(math.cos(aspect))
        # Angular width=width/range, at least2 beams; use larger transverse projection.
        n_beams = max(2, int(math.ceil(max(width_m, tang_m) / rng_m / fov_rad * BEAMS)))
        n_rbins = max(1, int(math.ceil(radial_m / m_per_rbin)))
        b_half = n_beams / 2.0
        b0, b1 = b_c - b_half, b_c + b_half
        r1 = r_c + n_rbins / 2.0
        echo_extents.append((cls, r_c - n_rbins / 2.0, r1, b0, b1))

        if cls == "uuv":  # Compact bright ellipse0.8-1.0; zero-intensity shadow1.5-3x size.
            _paint_footprint(canvas, r_c, b_c, length_m, width_m, aspect,
                             m_per_rbin, m_per_beam, float(rng.uniform(0.8, 1.0)), "ellipse")
            shadow_specs.append((r1, b0, b1,
                                 rng.uniform(1.5, 3.0) * length_m / m_per_rbin, 0.0))
        elif cls == "debris":  # Rectangle with bright0.9 edges and a long3-5x shadow.
            _paint_footprint(canvas, r_c, b_c, length_m, width_m, aspect,
                             m_per_rbin, m_per_beam, 0.5, "rect_edge", edge=0.9)
            shadow_specs.append((r1, b0, b1,
                                 rng.uniform(3.0, 5.0) * length_m / m_per_rbin, 0.0))
        else:  # Marine mammal:elongated0.5-0.8 ellipse, slight blur, short weak shadow.
            _paint_footprint(canvas, r_c, b_c, length_m, width_m, aspect,
                             m_per_rbin, m_per_beam, float(rng.uniform(0.5, 0.8)),
                             "ellipse", soft=True)
            shadow_specs.append((r1, b0, b1,
                                 rng.uniform(0.8, 1.5) * length_m / m_per_rbin, 0.25))

    for r1, b0, b1, sh_bins, strength in shadow_specs:  # Shadow extends into farther bins on the same beams.
        r_lo = int(max(0.0, math.floor(r1)))
        r_hi = int(min(float(RANGE_BINS), math.ceil(r1 + sh_bins)))
        b_lo = int(max(0.0, math.floor(b0)))
        b_hi = int(min(float(BEAMS), math.ceil(b1)))
        if r_lo < r_hi and b_lo < b_hi:
            canvas[r_lo:r_hi, b_lo:b_hi] *= strength

    _tvg_normalize(canvas)
    canvas = cv2.GaussianBlur(canvas, (0, 0), _BLUR_SIGMA)
    np.clip(canvas, 0.0, 1.0, out=canvas)

    img = _polar_to_sector(canvas, max_range_m, half_fov, size)
    return img, _annotations(echo_extents, max_range_m, half_fov, size)


# Polar canvas.

def _background(rng: np.random.Generator, noise: float) -> np.ndarray:
    """Rayleigh speckle, increasing range-dependent seabed return and random patches; nearest3% is
    dark. Clip/normalize speckle near1 so background peaks remain below target echoes0.5-1.0;
    unchecked Rayleigh tails would dominate normalized images.
    """
    rr = np.linspace(0.0, 1.0, RANGE_BINS)[:, None]
    base = 0.18 + 0.55 * rr  # Seabed return gradually increases with range.
    speckle = np.minimum(rng.rayleigh(scale=1.0, size=(RANGE_BINS, BEAMS)), 2.5) / 2.5
    canvas = speckle * base * (0.15 + 0.85 * float(noise))
    for _ in range(int(rng.integers(6, 15))):  # Soft elliptical seabed patches.
        r_c = rng.uniform(0.05, 0.95) * RANGE_BINS
        b_c = rng.uniform(0.0, BEAMS - 1.0)
        n_r = rng.uniform(8.0, 40.0)
        n_b = rng.uniform(6.0, 30.0)
        amp = rng.uniform(0.05, 0.20)
        i_lo = int(max(0.0, r_c - n_r / 2))
        i_hi = int(min(float(RANGE_BINS), r_c + n_r / 2))
        j_lo = int(max(0.0, b_c - n_b / 2))
        j_hi = int(min(float(BEAMS), b_c + n_b / 2))
        if i_lo >= i_hi or j_lo >= j_hi:
            continue
        gy, gx = np.mgrid[i_lo:i_hi, j_lo:j_hi].astype(np.float64)
        mask = ((gy - r_c) / (n_r / 2)) ** 2 + ((gx - b_c) / (n_b / 2)) ** 2 <= 1.0
        region = canvas[i_lo:i_hi, j_lo:j_hi]
        region += amp * base[i_lo:i_hi] * mask
    canvas[: max(1, int(round(0.03 * RANGE_BINS))), :] = 0.0  # Nearest3% of range bins form a dark band.
    return canvas


def _scatter_fish(
    rng: np.random.Generator,
    canvas: np.ndarray,
    r_c: float,
    b_c: float,
    m_per_rbin: float,
    m_per_beam: float,
) -> tuple[float, float, float, float]:
    """Fish school:20-80 small1-2-bin echoes, intensity0.3-0.6, within radius5-30m and no shadow.
    Return polar bounds accumulated from actual generated bright pixels, including their cell
    extents, not the sampling circle bounds.
    """
    radius_m = float(rng.uniform(5.0, 30.0))
    n = int(rng.integers(20, 81))
    ang = rng.uniform(0.0, 2.0 * np.pi, n)
    rad = radius_m * np.sqrt(rng.uniform(0.0, 1.0, n))  # Scatter uniformly within a disk.
    r_lo = r_hi = r_c
    b_lo = b_hi = b_c
    for k in range(n):
        pr = r_c + (rad[k] * math.cos(ang[k])) / m_per_rbin
        pb = b_c + (rad[k] * math.sin(ang[k])) / m_per_beam
        n_pr = int(rng.integers(1, 3))  # One or two bins.
        n_pb = int(rng.integers(1, 3))
        inten = float(rng.uniform(0.3, 0.6))
        i0 = int(max(0.0, math.floor(pr)))
        i1 = int(min(float(RANGE_BINS), math.ceil(pr) + n_pr - 1))
        j0 = int(max(0.0, math.floor(pb)))
        j1 = int(min(float(BEAMS), math.ceil(pb) + n_pb - 1))
        if i0 < i1 and j0 < j1:
            region = canvas[i0:i1, j0:j1]
            region[:] = np.maximum(region, inten)
        r_lo = min(r_lo, pr)               # Bounds accumulate actual bright points only.
        r_hi = max(r_hi, pr + n_pr)
        b_lo = min(b_lo, pb)
        b_hi = max(b_hi, pb + n_pb)
    return (
        max(0.0, r_lo),
        min(float(RANGE_BINS - 1), r_hi),
        max(0.0, b_lo),
        min(float(BEAMS - 1), b_hi),
    )


def _paint_footprint(
    canvas: np.ndarray,
    r_c: float,
    b_c: float,
    length_m: float,
    width_m: float,
    aspect: float,
    m_per_rbin: float,
    m_per_beam: float,
    intensity: float,
    shape: str,
    edge: float | None = None,
    soft: bool = False,
) -> None:
    """Paint the actual target footprint (length_m, width_m, aspect). Local metric coordinates are
    radial x and transverse y, rotated to long u/short v axes. ellipse draws an ellipse; rect_edge
    has brightest edges.
    """
    radial_m = length_m * abs(math.cos(aspect)) + width_m * abs(math.sin(aspect))
    tang_m = length_m * abs(math.sin(aspect)) + width_m * abs(math.cos(aspect))
    n_r = int(math.ceil(radial_m / m_per_rbin)) + 2
    n_b = int(math.ceil(tang_m / m_per_beam)) + 2
    i_lo = int(max(0.0, math.floor(r_c - n_r / 2)))
    i_hi = int(min(float(RANGE_BINS), math.ceil(r_c + n_r / 2)))
    j_lo = int(max(0.0, math.floor(b_c - n_b / 2)))
    j_hi = int(min(float(BEAMS), math.ceil(b_c + n_b / 2)))
    if i_lo >= i_hi or j_lo >= j_hi:
        return
    rr, bb = np.mgrid[i_lo:i_hi, j_lo:j_hi].astype(np.float64)
    x_m = (rr - r_c) * m_per_rbin  # Radial offset in meters.
    y_m = (bb - b_c) * m_per_beam  # Transverse offset in meters.
    ca, sa = math.cos(aspect), math.sin(aspect)
    u = x_m * ca + y_m * sa   # Along the target long axis.
    v = -x_m * sa + y_m * ca  # Along the target short axis.
    region = canvas[i_lo:i_hi, j_lo:j_hi]

    if shape == "ellipse":
        mask = (u / (length_m / 2)) ** 2 + (v / (width_m / 2)) ** 2 <= 1.0
        region[mask] = np.maximum(region[mask], intensity)
    elif shape == "rect_edge":
        em = np.maximum(np.abs(u) / (length_m / 2), np.abs(v) / (width_m / 2))
        inside = em <= 1.0
        fill = inside & (em < 0.85)
        border = inside & ~fill
        region[fill] = np.maximum(region[fill], intensity)
        region[border] = edge if edge is not None else intensity
    else:  # pragma: no cover - Defensive case.
        raise ValueError(f"Unknown shape {shape!r}")

    if soft:  # Slight marine-mammal blur.
        np.maximum(region, cv2.GaussianBlur(region, (0, 0), 1.0) * 0.9, out=region)


# Postprocessing.

def _tvg_normalize(canvas: np.ndarray) -> None:
    """Time-varying gain compensates the range-enhanced background, then peak-normalizes to [0,1]."""
    rr = np.linspace(0.0, 1.0, RANGE_BINS)[:, None]
    canvas *= 1.0 / (0.35 + 0.65 * rr)
    peak = float(canvas.max())
    if peak > 0.0:
        canvas /= peak


def _polar_to_sector(
    canvas: np.ndarray, max_range_m: float, half_fov: float, size: int
) -> np.ndarray:
    """Convert polar canvas to an upward sector with bottom-center apex and black exterior."""
    fov_rad = 2.0 * half_fov
    cx, cy, r_max_px = _sector_geometry(half_fov, size)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    dx = xs - cx
    dy = cy - ys  # Image y increases down; positive range projects upward.
    r_px = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dx, dy)  # Zero points upward; right is positive.
    inside = (r_px <= r_max_px) & (np.abs(theta) <= half_fov)
    map_r = (np.clip(r_px / np.float32(r_max_px), 0.0, 1.0) * (RANGE_BINS - 1)).astype(np.float32)
    map_b = (np.clip((theta + np.float32(half_fov)) / np.float32(fov_rad), 0.0, 1.0) * (BEAMS - 1)).astype(np.float32)
    img = cv2.remap(
        canvas.astype(np.float32), map_b, map_r,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0.0,
    )
    img[~inside] = 0.0
    return (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def _annotations(
    echo_extents: list[tuple[str, float, float, float, float]],
    max_range_m: float,
    half_fov: float,
    size: int,
) -> list[dict]:
    """Project four polar echo bounds to a clipped image rectangle; discard area below16 pixels."""
    fov_rad = 2.0 * half_fov
    out: list[dict] = []
    for cls, r0, r1, b0, b1 in echo_extents:
        if r0 >= RANGE_BINS or r1 < 0 or b0 >= BEAMS or b1 < 0:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for rb in (r0, r1):
            for bb in (b0, b1):
                rr = min(max(rb, 0.0), RANGE_BINS - 1.0) / (RANGE_BINS - 1)
                th = min(max(bb, 0.0), BEAMS - 1.0) / (BEAMS - 1) * fov_rad - half_fov
                x, y = _sector_pixel(rr, th, half_fov, size)
                xs.append(x)
                ys.append(y)
        x1 = int(max(0, math.floor(min(xs))))
        x2 = int(min(size - 1, math.ceil(max(xs))))
        y1 = int(max(0, math.floor(min(ys))))
        y2 = int(min(size - 1, math.ceil(max(ys))))
        if x2 > x1 and y2 > y1 and (x2 - x1) * (y2 - y1) >= _MIN_AREA_PX:
            out.append({"cls": cls, "bbox": [x1, y1, x2, y2]})
    return out
