"""Shared contract v1. Every public payload is validated before publication."""
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Cls = Literal["unknown", "uuv", "fish_school", "debris", "marine_mammal", "vessel"]
Level = Literal[0, 1, 2, 3]
Mode = Literal["security", "disaster"]
Network = Literal["online", "offline"]
ZoneState = Literal["open", "restricted", "clear", "unsurveyed", "blocked"]
UnitFloat = Annotated[float, Field(ge=0, le=1)]
Nonnegative = Annotated[float, Field(ge=0)]
Point = tuple[float, float, float, float]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ErrorEllipse(ContractModel):
    a_m: Nonnegative
    b_m: Nonnegative
    angle_deg: float


class RiskBreakdown(ContractModel):
    C: UnitFloat
    P: UnitFloat
    B: UnitFloat
    Z: UnitFloat
    D: UnitFloat


class Buoy(ContractModel):
    id: str
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    status: Literal["ok", "down"]
    range_m: Nonnegative
    pinging: bool


class Track(ContractModel):
    id: str
    status: Literal["tentative", "confirmed"]
    cls: Cls
    conf: UnitFloat
    cue: Literal["narrowband", "broadband", "call", "none"]
    lat: float
    lon: float
    depth_m: Nonnegative
    vel_e: float
    vel_n: float
    vel_d: float
    speed_mps: Nonnegative
    heading_deg: float
    err: ErrorEllipse
    history: list[Point]
    predicted: list[Point]
    level: Level
    risk: UnitFloat
    detection_id: str | None


class Alert(ContractModel):
    id: str
    track_id: str
    level: Literal[1, 2, 3]
    risk: UnitFloat
    breakdown: RiskBreakdown
    zone_id: str | None
    asset_id: str
    distance_m: Nonnegative
    eta_s: Nonnegative | None
    raised_t: Nonnegative
    updated_t: Nonnegative
    options_ready: bool


class ZoneStatus(ContractModel):
    id: str
    state: ZoneState
    coverage: UnitFloat


class Asset(ContractModel):
    id: str
    name: str
    kind: str
    lat: float
    lon: float
    sensitivity: UnitFloat
    rings_m: tuple[Nonnegative, Nonnegative, Nonnegative]


class Detection(ContractModel):
    id: str
    track_id: str
    buoy_id: str
    t: Nonnegative
    cls: Cls
    conf: UnitFloat
    bbox: tuple[float, float, float, float]
    image_url: str
    model: Literal["yolo26n", "stub"]


class Option(ContractModel):
    id: str
    label: str
    is_baseline: bool
    zones_closed: list[str]
    speed_limit_zones: list[str]
    berths_open_pct: UnitFloat
    vessels_affected: Annotated[int, Field(ge=0)]
    delay_vessel_hours: Nonnegative
    residual_risk: UnitFloat


class OptionsPayload(ContractModel):
    alert_id: str
    options: list[Option]
    ranked: list[str]


class ReopenPlan(ContractModel):
    route_zone_ids: list[str]
    reopen_berth_zone_ids: list[str]
    unsurveyed_zone_ids: list[str]
    blocked_zone_ids: list[str]
    est_hours_saved: Nonnegative


class Recommendation(ContractModel):
    id: str
    kind: Literal["security", "disaster", "buoy"]
    alert_id: str | None
    model: Literal["cloud", "local", "template"]
    summary: Annotated[str, Field(max_length=60)]
    explanation: Annotated[str, Field(max_length=300)]
    recommended_option_id: str | None
    evidence_ids: list[str]
    uncertainties: list[str]
    confidence: Literal["low", "medium", "high"]
    created_t: Nonnegative
    latency_ms: Nonnegative


class LogEntry(ContractModel):
    t: Nonnegative
    level: Literal["info", "warn", "critical"]
    source: Literal["sim", "perception", "decision", "agent", "operator"]
    text: str


class StateMsg(ContractModel):
    type: Literal["state"]
    seq: Annotated[int, Field(ge=0)]
    t: Nonnegative
    mode: Mode
    network: Network
    scenario: Literal["a", "b"] | None
    paused: bool
    speed: Annotated[float, Field(gt=0)]
    buoys: list[Buoy]
    tracks: list[Track]
    alerts: list[Alert]
    zones: list[ZoneStatus]


class AlertRaised(ContractModel):
    alert: Alert


class AlertChanged(AlertRaised):
    from_level: Level
    to_level: Level


class AlertCleared(ContractModel):
    alert_id: str


class DetectionEvent(ContractModel):
    detection: Detection


class RecommendationEvent(ContractModel):
    recommendation: Recommendation


class DecisionRequest(ContractModel):
    alert_id: str
    option_id: str
    action: Literal["approve", "reject"]
    operator: Annotated[str, Field(min_length=1, max_length=100)]


class ZoneChanged(ContractModel):
    zone_id: str
    state: ZoneState


class BuoyChanged(ContractModel):
    buoy_id: str
    status: Literal["ok", "down"]


class NetworkChanged(ContractModel):
    network: Network


class ModeChanged(ContractModel):
    mode: Mode


class ScenarioChanged(ContractModel):
    scenario: Literal["a", "b"] | None
    status: Literal["started", "ended", "reset"]


class LogEvent(ContractModel):
    log: LogEntry


EVENT_DATA = {
    "alert_raised": AlertRaised, "alert_changed": AlertChanged, "alert_cleared": AlertCleared,
    "detection": DetectionEvent, "options_ready": OptionsPayload, "recommendation": RecommendationEvent,
    "decision": DecisionRequest, "zone_changed": ZoneChanged, "reopen_plan": ReopenPlan,
    "buoy_changed": BuoyChanged, "network_changed": NetworkChanged, "mode_changed": ModeChanged,
    "scenario_changed": ScenarioChanged, "log": LogEvent,
}


class EventMsg(ContractModel):
    type: Literal["event"]
    seq: Annotated[int, Field(ge=0)]
    t: Nonnegative
    event: str
    data: dict[str, Any]

    @model_validator(mode="after")
    def validate_event_data(self):
        if self.event not in EVENT_DATA:
            raise ValueError(f"Unknown contract v1 event: {self.event}")
        self.data = EVENT_DATA[self.event].model_validate(self.data).model_dump(mode="json")
        return self


class Ok(ContractModel):
    ok: Literal[True] = True


class StartRequest(ContractModel):
    speed: Annotated[float, Field(gt=0, le=100)] | None = None


class ControlRequest(ContractModel):
    action: Literal["pause", "resume", "speed", "reset"]
    value: Annotated[float, Field(gt=0, le=100)] | None = None

    @model_validator(mode="after")
    def speed_requires_value(self):
        if self.action == "speed" and self.value is None:
            raise ValueError("speed requires a positive value")
        return self


class ModeRequest(ContractModel):
    mode: Mode


class InjectRequest(ContractModel):
    type: Literal["buoy_down", "buoy_up", "network_down", "network_up", "noise_up", "noise_down"]
    target: str | None = None

    @model_validator(mode="after")
    def buoy_requires_target(self):
        if self.type.startswith("buoy_") and not self.target:
            raise ValueError("buoy fault requires target")
        return self


class LogRequest(ContractModel):
    level: Literal["info", "warn", "critical"]
    source: Literal["sim", "perception", "decision", "agent", "operator"]
    text: Annotated[str, Field(min_length=1, max_length=2000)]


class AskRequest(ContractModel):
    question: Annotated[str, Field(min_length=1, max_length=4000)]
    track_id: str | None = None


class AskResponse(ContractModel):
    answer: str
    model: str


class Metrics(ContractModel):
    yolo: Any | None
    lora: Any | None


class ZoneProperties(ContractModel):
    id: str
    name: str
    kind: Literal["berth", "channel", "anchorage"]
    sensitivity: UnitFloat
    berths: Annotated[int, Field(ge=0)]
    neighbors: list[str]
    entrance: bool
    state: ZoneState | None = None
    coverage: UnitFloat | None = None


class Geometry(ContractModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list


class ZoneFeature(ContractModel):
    type: Literal["Feature"]
    properties: ZoneProperties
    geometry: Geometry


class ZoneCollection(ContractModel):
    type: Literal["FeatureCollection"]
    features: list[ZoneFeature]
