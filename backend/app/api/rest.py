"""HTTP contract v1. Mutable state is owned by the single application engine."""
import json

import httpx
from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import Response

from .. import config
from ..models import (
    Alert,
    AskRequest,
    AskResponse,
    Asset,
    Buoy,
    ControlRequest,
    DecisionRequest,
    Detection,
    EventMsg,
    InjectRequest,
    LogEntry,
    LogRequest,
    Metrics,
    ModeRequest,
    Ok,
    OptionsPayload,
    Recommendation,
    StartRequest,
    StateMsg,
    Track,
    ZoneCollection,
)

router = APIRouter(prefix="/api")


def _reject_nonfinite_json(value):
    raise ValueError(f"Invalid JSON numeric value: {value}")


def engine(request: Request):
    return request.app.state.engine


def found(value, description):
    if value is None:
        raise HTTPException(404, f"Unknown {description}")
    return value


@router.get("/health", response_model=Ok)
async def health(request: Request):
    if getattr(request.app.state, "runtime_error", None) or engine(request).persistence_error:
        raise HTTPException(503, "Backend runtime or durable history unavailable; inspect server logs")
    return Ok()


@router.get("/state", response_model=StateMsg)
async def state(request: Request):
    return engine(request).state()


@router.get("/events", response_model=list[EventMsg])
async def events(request: Request, since_seq: int = Query(0, ge=0)):
    return engine(request).bus.since(since_seq)


@router.get("/zones", response_model=ZoneCollection)
async def zones(request: Request):
    return engine(request).zones_geojson()


@router.get("/assets", response_model=list[Asset])
async def assets(request: Request):
    return engine(request).assets


@router.get("/buoys", response_model=list[Buoy])
async def buoys(request: Request):
    return list(engine(request).world.buoys.values())


@router.get("/tracks/{track_id}", response_model=Track)
async def track(request: Request, track_id: str):
    return found(engine(request).detail("track", track_id), f"track: {track_id}")


@router.get("/alerts/{alert_id}", response_model=Alert)
async def alert(request: Request, alert_id: str):
    return found(engine(request).detail("alert", alert_id), f"alert: {alert_id}")


@router.get("/detections/{det_id}", response_model=Detection)
async def detection(request: Request, det_id: str):
    return found(engine(request).detail("detection", det_id), f"detection: {det_id}")


@router.get("/options/{alert_id}", response_model=OptionsPayload)
async def options(request: Request, alert_id: str):
    return found(engine(request).detail("options", alert_id), f"options for alert: {alert_id}")


@router.get("/sonar/{det_id}.png", response_class=Response)
async def sonar(request: Request, det_id: str):
    image = found(engine(request).image(det_id), f"sonar image: {det_id}")
    return Response(image, media_type="image/png", headers={"Cache-Control":"no-cache"})


@router.get("/log", response_model=list[LogEntry])
async def logs(request: Request, limit: int = Query(100, ge=1, le=config.LOG_CACHE_SIZE)):
    return list(engine(request).logs)[:limit]


@router.get("/metrics", response_model=Metrics)
async def metrics():
    result = {}
    for kind in ("yolo", "lora"):
        try:
            result[kind] = json.loads((config.ROOT/"ml"/kind/"metrics.json").read_text(encoding="utf-8"),
                                      parse_constant=_reject_nonfinite_json)
        except (OSError, ValueError):
            result[kind] = None
    return result


@router.post("/scenario/{scenario_id}/start", response_model=Ok)
async def start(request: Request, scenario_id: str, body: StartRequest | None = Body(None)):
    if scenario_id not in ("a", "b"):
        raise HTTPException(404, "Scenario must be a or b")
    engine(request).start(scenario_id, body.speed if body else None)
    request.app.state.runtime_error = None
    return Ok()


@router.post("/control", response_model=Ok)
async def control(request: Request, body: ControlRequest):
    game = engine(request)
    try:
        game.control(body.action, body.value)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if body.action == "reset":
        request.app.state.runtime_error = None
    return Ok()


@router.post("/mode", response_model=Ok)
async def mode(request: Request, body: ModeRequest):
    engine(request).set_mode(body.mode)
    return Ok()


@router.post("/inject", response_model=Ok)
async def inject(request: Request, body: InjectRequest):
    try:
        engine(request).inject(body.type, body.target)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Ok()


@router.post("/decision", response_model=Ok)
async def decision(request: Request, body: DecisionRequest):
    game = engine(request)
    try:
        game.decide(body.alert_id, body.option_id, body.action, body.operator)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return Ok()


@router.post("/recommendations", response_model=Ok)
async def recommendations(request: Request, body: Recommendation):
    try:
        engine(request).recommend(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Ok()


@router.post("/log", response_model=Ok)
async def append_log(request: Request, body: LogRequest):
    engine(request).log(body.level, body.source, body.text)
    return Ok()


@router.post("/agent/ask", response_model=AskResponse)
async def ask(request: Request, body: AskRequest):
    try:
        response = await request.app.state.agent_client.post(config.AGENT_URL, json=body.model_dump(mode="json"))
        response.raise_for_status()
        return AskResponse.model_validate(response.json())
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Agent timed out after 20 seconds; check localhost:8001") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Agent unavailable or returned an invalid response; start Agent on port 8001") from exc
