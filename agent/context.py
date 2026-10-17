"""上下文收集（C3）：REST 拉齐事实，压缩到 ≤ 3 KB。

格式与任务书 C3 的上下文 JSON 一致（供云端/本地/模板三处共用）；
history_summary 由航迹 history 计算：
近 60 秒深度标准差与直线度；covering_track 为距离小于 range_m 的在线浮标。
"""

from __future__ import annotations

import json
import math

import httpx

from .backend_client import BackendClient

LAT0, LON0 = 33.7300, -118.2600  # 共享契约：本地米制坐标原点
M_PER_LAT = 110540.0
M_PER_LON = 111320.0 * math.cos(math.radians(LAT0))
MAX_CONTEXT_BYTES = 3 * 1024
HISTORY_WINDOW_S = 60.0


def _xy(point: list) -> tuple[float, float]:
    lat, lon = point[0], point[1]
    return (lon - LON0) * M_PER_LON, (lat - LAT0) * M_PER_LAT


def history_summary(history: list, t_now: float, window_s: float = HISTORY_WINDOW_S) -> dict:
    """近 window_s 秒的深度标准差与直线度（弦长/路径长，1.0 = 直线）。"""
    pts = [p for p in history if len(p) >= 4 and 0.0 <= t_now - float(p[3]) <= window_s]
    if len(pts) < 2:
        return {"depth_std_m": 0.0, "straightness": 1.0}
    depths = [float(p[2]) for p in pts]
    mean = sum(depths) / len(depths)
    std = math.sqrt(sum((d - mean) ** 2 for d in depths) / len(depths))
    path = 0.0
    for a, b in zip(pts, pts[1:]):
        (x1, y1), (x2, y2) = _xy(a), _xy(b)
        path += math.hypot(x2 - x1, y2 - y1)
    (x1, y1), (x2, y2) = _xy(pts[0]), _xy(pts[-1])
    chord = math.hypot(x2 - x1, y2 - y1)
    straightness = 1.0 if path <= 0 else max(0.0, min(1.0, chord / path))
    return {"depth_std_m": round(std, 2), "straightness": round(straightness, 3)}


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return math.hypot((lat1 - lat2) * M_PER_LAT, (lon1 - lon2) * M_PER_LON)


def _slim_track(track: dict | None, t_now: float) -> dict | None:
    if not track:
        return None
    keep = ("id", "status", "cls", "conf", "cue", "lat", "lon",
            "depth_m", "speed_mps", "heading_deg", "level", "risk", "detection_id")
    slim = {k: track.get(k) for k in keep if track.get(k) is not None}
    slim["history_summary"] = history_summary(track.get("history", []), t_now)
    return slim


def _slim_detection(d: dict) -> dict:
    return {k: d.get(k) for k in ("id", "cls", "conf", "model") if d.get(k) is not None}


def _trim(context: dict, limit: int = MAX_CONTEXT_BYTES) -> dict:
    """按 UTF-8 实际字节逐级裁剪到 3 KB，同时保留模板决策所需事实。"""
    def size(c: dict) -> int:
        return len(json.dumps(c, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    if size(context) <= limit:
        return context
    context["recent_logs"] = [t[:40] for t in context.get("recent_logs", [])][:3]
    if size(context) <= limit:
        return context
    context.pop("recent_logs", None)
    if size(context) <= limit:
        return context
    context["zones"] = [{"id": z.get("id"), "state": z.get("state")} for z in context.get("zones", [])]
    if size(context) <= limit:
        return context
    context["detections"] = context.get("detections", [])[:2]
    if size(context) <= limit:
        return context
    # Option 的完整字段已由后端校验；模板只需以下指标和关闭分区数量。
    option_fields = (
        "id", "label", "zones_closed", "vessels_affected",
        "delay_vessel_hours", "residual_risk",
    )
    context["options"] = [
        {k: option.get(k) for k in option_fields if k in option}
        for option in context.get("options", [])
    ]
    if size(context) <= limit:
        return context
    # security 的分区详情可由方案里的 zones_closed ID 代替；灾害/浮标必须保留状态。
    if context.get("kind") == "security":
        context["zones"] = []
    for option in context.get("options", []):
        if "zones_closed" in option:
            option["zones_closed_count"] = len(option["zones_closed"] or [])
            option.pop("zones_closed", None)
    if size(context) <= limit:
        return context
    context["detections"] = []
    if size(context) > limit:
        raise ValueError(f"上下文压缩后仍超过 {limit} 字节")
    return context


async def collect_security(
    client: BackendClient,
    alert_id: str,
    options: list | None = None,
    ranked: list | None = None,
) -> dict:
    """按真实 alert_id 拉齐安全事件上下文。

    事件里的 options/ranked 已带则直接用；缺失时回退 GET /api/options/{alert_id}。
    警报已不存在（场景重置等）时抛 httpx.HTTPStatusError(404)，由调用方丢弃任务。
    """
    alert = await client.get_alert(alert_id)
    state = await client.get_state()
    t_now = float(state.get("t", 0.0))

    track: dict | None = None
    if alert.get("track_id"):
        try:
            track = await client.get_track(alert["track_id"])
        except httpx.HTTPStatusError:
            track = None

    detections: list[dict] = []
    if track and track.get("detection_id"):
        try:
            detections.append(_slim_detection(await client.get_detection(track["detection_id"])))
        except httpx.HTTPStatusError:
            pass

    if options is None or ranked is None:
        payload = await client.get_options(alert_id)
        options, ranked = payload.get("options", []), payload.get("ranked", [])

    buoys = await client.get_buoys()
    ok_buoys = [b for b in buoys if b.get("status") == "ok"]
    down = [b["id"] for b in buoys if b.get("status") == "down"]
    covering: list[str] = []
    if track:
        covering = [
            b["id"] for b in ok_buoys
            if distance_m(float(b["lat"]), float(b["lon"]),
                          float(track["lat"]), float(track["lon"])) < float(b["range_m"])
        ]

    try:
        recent_logs = [l.get("text", "") for l in await client.get_logs(10)]
    except httpx.HTTPStatusError:
        recent_logs = []

    context = {
        "kind": "security",
        "t": t_now,
        "mode": state.get("mode"),
        "network": state.get("network"),
        "alert": alert,
        "track": _slim_track(track, t_now),
        "detections": detections,
        "options": options,
        "ranked": list(ranked),
        "buoys": {"ok": len(ok_buoys), "down": down, "covering_track": covering},
        "zones": state.get("zones", []),
        "recent_logs": recent_logs,
    }
    return _trim(context)


def _buoy_facts(buoys: list[dict]) -> dict:
    ok_ids = [b["id"] for b in buoys if b.get("status") == "ok" and b.get("id")]
    down = [b["id"] for b in buoys if b.get("status") == "down" and b.get("id")]
    return {"ok": len(ok_ids), "ok_ids": ok_ids, "down": down}


async def collect_disaster(client: BackendClient, plan: dict) -> dict:
    """reopen_plan 的真实计划、分区状态和浮标状态上下文。"""
    state = await client.get_state()
    buoys = await client.get_buoys()
    context = {
        "kind": "disaster",
        "t": float(state.get("t", 0.0)),
        "mode": state.get("mode"),
        "network": state.get("network"),
        "reopen_plan": dict(plan),
        "buoys": _buoy_facts(buoys),
        "zones": [
            {key: zone.get(key) for key in ("id", "state", "coverage") if key in zone}
            for zone in state.get("zones", [])
        ],
        "options": [],
        "ranked": [],
        "recent_logs": [],
    }
    return _trim(context)


def _rings(geometry: dict) -> list[list[list[float]]]:
    coordinates = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        return coordinates[:1]
    if geometry.get("type") == "MultiPolygon":
        return [polygon[0] for polygon in coordinates if polygon]
    return []


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    points = [((lon - LON0) * M_PER_LON, (lat - LAT0) * M_PER_LAT) for lon, lat in ring]
    j = len(points) - 1
    for i, (xi, yi) in enumerate(points):
        xj, yj = points[j]
        if (yi > y) != (yj > y):
            crossing = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < crossing:
                inside = not inside
        j = i
    return inside


def _segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy))


def _zone_in_range(buoy: dict, feature: dict) -> bool:
    bx = (float(buoy["lon"]) - LON0) * M_PER_LON
    by = (float(buoy["lat"]) - LAT0) * M_PER_LAT
    limit = float(buoy["range_m"])
    for ring in _rings(feature.get("geometry") or {}):
        if _point_in_ring(bx, by, ring):
            return True
        points = [((lon - LON0) * M_PER_LON, (lat - LAT0) * M_PER_LAT) for lon, lat in ring]
        for first, second in zip(points, points[1:] + points[:1]):
            if _segment_distance(bx, by, *first, *second) <= limit:
                return True
    return False


async def collect_buoy(client: BackendClient, buoy_id: str) -> dict:
    """浮标失效上下文；覆盖影响只声明量程圆与分区几何相交这一可复算事实。"""
    state = await client.get_state()
    buoys = await client.get_buoys()
    target = next((b for b in buoys if b.get("id") == buoy_id), None)
    if target is None:
        raise ValueError(f"浮标 {buoy_id} 已不存在")
    zones_geojson = await client.get_zones()
    features = zones_geojson.get("features", [])
    affected = sorted(
        feature.get("properties", {}).get("id")
        for feature in features
        if feature.get("properties", {}).get("id") and _zone_in_range(target, feature)
    )
    remaining_by_zone = {}
    for zone_id in affected:
        remaining_by_zone[zone_id] = sorted(
            buoy["id"]
            for buoy in buoys
            if buoy.get("status") == "ok"
            and any(
                feature.get("properties", {}).get("id") == zone_id and _zone_in_range(buoy, feature)
                for feature in features
            )
        )
    context = {
        "kind": "buoy",
        "t": float(state.get("t", 0.0)),
        "mode": state.get("mode"),
        "network": state.get("network"),
        "buoy": {key: target.get(key) for key in ("id", "status", "range_m")},
        "buoys": _buoy_facts(buoys),
        "coverage_impact": {
            "method": "buoy_range_intersects_zone_geometry",
            "affected_zone_ids": affected,
            "remaining_ok_buoy_ids_by_zone": remaining_by_zone,
        },
        "zones": [
            {key: zone.get(key) for key in ("id", "state", "coverage") if key in zone}
            for zone in state.get("zones", []) if zone.get("id") in affected
        ],
        "options": [],
        "ranked": [],
        "recent_logs": [],
    }
    return _trim(context)


def context_ids(context: dict) -> set[str]:
    """上下文中真实存在的全部 ID（双重校验的第一重依据）。"""
    ids: set[str] = set()
    if a := context.get("alert"):
        ids.add(a.get("id"))
    if t := context.get("track"):
        ids.add(t.get("id"))
        if t.get("detection_id"):
            ids.add(t["detection_id"])
    for d in context.get("detections", []):
        ids.add(d.get("id"))
    for o in context.get("options", []):
        ids.add(o.get("id"))
        ids |= set(o.get("zones_closed", [])) | set(o.get("speed_limit_zones", []))
    ids |= {r for r in context.get("ranked", [])}
    buoys = context.get("buoys", {})
    ids |= set(buoys.get("covering_track", [])) | set(buoys.get("down", []))
    for z in context.get("zones", []):
        ids.add(z.get("id"))
    if b := context.get("buoy"):
        ids.add(b.get("id"))
    plan = context.get("reopen_plan") or {}
    for key in ("route_zone_ids", "reopen_berth_zone_ids", "unsurveyed_zone_ids", "blocked_zone_ids"):
        ids |= set(plan.get(key, []))
    impact = context.get("coverage_impact") or {}
    ids |= set(impact.get("affected_zone_ids", []))
    for buoy_ids in (impact.get("remaining_ok_buoy_ids_by_zone") or {}).values():
        ids |= set(buoy_ids)
    ids |= set(buoys.get("ok_ids", []))
    return {i for i in ids if i}
