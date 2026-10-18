"""ml.sonar.render —— 扇形前视声呐灰度图渲染器（C1）。

共享契约 v1 §7 接口：签名与返回格式一字不改（B 直接 import）。

几何约定（与任务书 C1 一致）：
- 极坐标画布 512 距离格 × 256 波束；距离格均匀覆盖 [0, max_range_m]，
  波束均匀覆盖 [-fov/2, +fov/2]（bearing 相对声呐正前方，0 为正前，右正）。
- 输出 size×size：扇形顶点在底部中央、向上张开；扇形完整放入画面，
  最大量程的像素半径 r_max = min(size-1, (size/2-1)/sin(fov/2))，
  扇形外像素为 0（黑）。
- 声影在目标更远一侧（径向向外）：uuv/debris 零强度，marine_mammal 短而弱，
  fish_school 无声影。标注框只包回波，不含声影。
- 所有随机性来自本地 np.random.default_rng(seed)，不触碰全局随机状态；
  同一 seed 输出逐像素一致。
"""

from __future__ import annotations

import math
from numbers import Integral

import cv2
import numpy as np

# 极坐标画布分辨率（任务书 C1：512 距离格 × 256 波束）
RANGE_BINS = 512
BEAMS = 256

# YOLO 类别 ID（共享契约）：0 uuv，1 fish_school，2 debris，3 marine_mammal
CLASS_NAMES: tuple[str, ...] = ("uuv", "fish_school", "debris", "marine_mammal")

_MIN_AREA_PX = 16   # 标注框最小像素面积，低于则丢弃
_BLUR_SIGMA = 0.7   # 任务书：高斯模糊 σ = 0.7


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
    """targets 每项: {"cls": "uuv" | "fish_school" | "debris" | "marine_mammal",
                      "range_m": float, "bearing_deg": float,   # 相对声呐正前方，-fov/2 到 fov/2
                      "length_m": float, "width_m": float, "aspect_deg": float}
    返回: (size×size 灰度 uint8 图像，扇形顶点在底部中央,
           标注 [{"cls": str, "bbox": [x1, y1, x2, y2]}]，单位像素)"""
    if not 0.0 < fov_deg < 180.0:
        raise ValueError(f"fov_deg 需在 (0, 180) 内，收到 {fov_deg}")
    if max_range_m <= 0.0:
        raise ValueError(f"max_range_m 需为正，收到 {max_range_m}")
    if size < 16:
        raise ValueError(f"size 过小: {size}")

    rng = np.random.default_rng(seed)  # 本地生成器：不污染全局随机状态
    half_fov = math.radians(fov_deg) / 2.0
    fov_rad = 2.0 * half_fov

    canvas = _background(rng, noise)

    echo_extents: list[tuple[str, float, float, float, float]] = []
    # (远端距离格 r1, 波束 b0, 波束 b1, 影长(格), 强度)
    shadow_specs: list[tuple[float, float, float, float, float]] = []

    for t in targets:
        cls = str(t["cls"])
        if cls not in CLASS_NAMES:
            raise ValueError(f"未知类别 {cls!r}；可选: {CLASS_NAMES}")
        rng_m = max(float(t["range_m"]), 1e-3)
        theta = math.radians(float(t["bearing_deg"]))
        length_m = max(float(t["length_m"]), 0.1)
        width_m = max(float(t["width_m"]), 0.1)
        aspect = math.radians(float(t["aspect_deg"]))

        m_per_rbin = max_range_m / RANGE_BINS
        m_per_beam = rng_m * fov_rad / BEAMS          # 该距离处每波束对应横向米数
        r_c = rng_m / max_range_m * (RANGE_BINS - 1)  # 目标中心的距离格
        b_c = (theta + half_fov) / fov_rad * (BEAMS - 1)

        if cls == "fish_school":
            echo_extents.append(
                (cls, *_scatter_fish(rng, canvas, r_c, b_c, m_per_rbin, m_per_beam))
            )
            continue

        # 径向长度 = 目标在视线方向上的投影；横向同理
        radial_m = length_m * abs(math.cos(aspect)) + width_m * abs(math.sin(aspect))
        tang_m = length_m * abs(math.sin(aspect)) + width_m * abs(math.cos(aspect))
        # 角宽 = 宽度 ÷ 距离（契约口径，至少 2 波束）；横向投影更大时取大者
        n_beams = max(2, int(math.ceil(max(width_m, tang_m) / rng_m / fov_rad * BEAMS)))
        n_rbins = max(1, int(math.ceil(radial_m / m_per_rbin)))
        b_half = n_beams / 2.0
        b0, b1 = b_c - b_half, b_c + b_half
        r1 = r_c + n_rbins / 2.0
        echo_extents.append((cls, r_c - n_rbins / 2.0, r1, b0, b1))

        if cls == "uuv":  # 紧凑亮椭圆 0.8–1.0；零强度声影 1.5–3 倍尺寸
            _paint_footprint(canvas, r_c, b_c, length_m, width_m, aspect,
                             m_per_rbin, m_per_beam, float(rng.uniform(0.8, 1.0)), "ellipse")
            shadow_specs.append((r1, b0, b1,
                                 rng.uniform(1.5, 3.0) * length_m / m_per_rbin, 0.0))
        elif cls == "debris":  # 矩形、边缘最亮 0.9；声影长且明显 3–5 倍
            _paint_footprint(canvas, r_c, b_c, length_m, width_m, aspect,
                             m_per_rbin, m_per_beam, 0.5, "rect_edge", edge=0.9)
            shadow_specs.append((r1, b0, b1,
                                 rng.uniform(3.0, 5.0) * length_m / m_per_rbin, 0.0))
        else:  # marine_mammal：拉长椭圆 0.5–0.8、轻微模糊；声影短而弱
            _paint_footprint(canvas, r_c, b_c, length_m, width_m, aspect,
                             m_per_rbin, m_per_beam, float(rng.uniform(0.5, 0.8)),
                             "ellipse", soft=True)
            shadow_specs.append((r1, b0, b1,
                                 rng.uniform(0.8, 1.5) * length_m / m_per_rbin, 0.25))

    for r1, b0, b1, sh_bins, strength in shadow_specs:  # 声影：同波束、更远距离格
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


# ---------------------------------------------------------------- 极坐标画布

def _background(rng: np.random.Generator, noise: float) -> np.ndarray:
    """瑞利斑点噪声 + 随距离增强的海底回波 + 随机斑块；近距 3% 为暗带。

    斑点噪声截尾归一（上限 ~1），保证背景峰值明显低于目标回波强度（0.5–1.0），
    否则瑞利长尾会在归一化后盖过目标、图像整体发灰。
    """
    rr = np.linspace(0.0, 1.0, RANGE_BINS)[:, None]
    base = 0.18 + 0.55 * rr  # 海底回波随距离逐渐增强
    speckle = np.minimum(rng.rayleigh(scale=1.0, size=(RANGE_BINS, BEAMS)), 2.5) / 2.5
    canvas = speckle * base * (0.15 + 0.85 * float(noise))
    for _ in range(int(rng.integers(6, 15))):  # 海底随机斑块（椭圆，柔和）
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
    canvas[: max(1, int(round(0.03 * RANGE_BINS))), :] = 0.0  # 最近 3% 距离格暗带
    return canvas


def _scatter_fish(
    rng: np.random.Generator,
    canvas: np.ndarray,
    r_c: float,
    b_c: float,
    m_per_rbin: float,
    m_per_beam: float,
) -> tuple[float, float, float, float]:
    """鱼群：半径 5–30 m 内撒 20–80 个 1–2 格小亮点（强度 0.3–0.6），无声影。

    返回极坐标外包 (r0, r1, b0, b1)——由**实际生成的亮点**（含各点 1–2 格
    亮块的占格范围）累计得到，不使用采样圆的外接框。
    """
    radius_m = float(rng.uniform(5.0, 30.0))
    n = int(rng.integers(20, 81))
    ang = rng.uniform(0.0, 2.0 * np.pi, n)
    rad = radius_m * np.sqrt(rng.uniform(0.0, 1.0, n))  # 圆盘内均匀撒点
    r_lo = r_hi = r_c
    b_lo = b_hi = b_c
    for k in range(n):
        pr = r_c + (rad[k] * math.cos(ang[k])) / m_per_rbin
        pb = b_c + (rad[k] * math.sin(ang[k])) / m_per_beam
        n_pr = int(rng.integers(1, 3))  # 1–2 格
        n_pb = int(rng.integers(1, 3))
        inten = float(rng.uniform(0.3, 0.6))
        i0 = int(max(0.0, math.floor(pr)))
        i1 = int(min(float(RANGE_BINS), math.ceil(pr) + n_pr - 1))
        j0 = int(max(0.0, math.floor(pb)))
        j1 = int(min(float(BEAMS), math.ceil(pb) + n_pb - 1))
        if i0 < i1 and j0 < j1:
            region = canvas[i0:i1, j0:j1]
            region[:] = np.maximum(region, inten)
        r_lo = min(r_lo, pr)               # 外包只由实际点累计
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
    """在目标真实足印（长 length_m、宽 width_m、朝向 aspect）内上色。

    以目标中心为原点的米制局部坐标系：径向为 x、横向为 y，旋转 aspect 后
    长轴 u、短轴 v。ellipse = 椭圆；rect_edge = 矩形、边缘最亮。
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
    x_m = (rr - r_c) * m_per_rbin  # 径向偏移（米）
    y_m = (bb - b_c) * m_per_beam  # 横向偏移（米）
    ca, sa = math.cos(aspect), math.sin(aspect)
    u = x_m * ca + y_m * sa   # 沿目标长轴
    v = -x_m * sa + y_m * ca  # 沿目标短轴
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
    else:  # pragma: no cover - 防御
        raise ValueError(f"未知形状 {shape!r}")

    if soft:  # marine_mammal 轻微模糊
        np.maximum(region, cv2.GaussianBlur(region, (0, 0), 1.0) * 0.9, out=region)


# ---------------------------------------------------------------- 后处理

def _tvg_normalize(canvas: np.ndarray) -> None:
    """时变增益归一化：随距离压低增益补偿背景增强，再按峰值归一到 [0, 1]。"""
    rr = np.linspace(0.0, 1.0, RANGE_BINS)[:, None]
    canvas *= 1.0 / (0.35 + 0.65 * rr)
    peak = float(canvas.max())
    if peak > 0.0:
        canvas /= peak


def _polar_to_sector(
    canvas: np.ndarray, max_range_m: float, half_fov: float, size: int
) -> np.ndarray:
    """极坐标 → 扇形：顶点在底部中央、向上张开；扇形外为黑。"""
    fov_rad = 2.0 * half_fov
    cx, cy, r_max_px = _sector_geometry(half_fov, size)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    dx = xs - cx
    dy = cy - ys  # 图像 y 向下，取正后向上
    r_px = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dx, dy)  # 0 = 正上，右正
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
    """回波极坐标外包四角 → 图像坐标最小外接矩形；裁到图内，面积 < 16 px 丢弃。"""
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
