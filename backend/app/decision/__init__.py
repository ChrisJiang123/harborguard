"""Decision integration. Proposed options never change zone access by themselves."""
from __future__ import annotations

from .. import config
from .alerts import AlertManager
from .disaster import DisasterSurvey
from .optimizer import Optimizer
from .pinger import Pinger
from .risk import RiskScorer
from .zones import Zones


class DecisionEngine:
    def __init__(self, zones_geojson: dict, assets: list[dict], vessels: list[dict], classifier=None):
        self.zones = Zones(zones_geojson, assets)
        self.optimizer = Optimizer(self.zones, vessels)
        self.classifier = classifier
        self.reset()

    def reset(self, mode="security"):
        # Names remain unique during this server lifetime, so a delayed operator
        # request or cached sonar URL cannot refer to a different scenario object.
        previous_alert_counter = getattr(getattr(self, "alert_manager", None), "counter", 0)
        previous_detection_counter = getattr(getattr(self, "pinger", None), "counter", 0)
        self.mode = mode
        self.risk = RiskScorer(self.zones)
        self.alert_manager = AlertManager()
        self.alert_manager.counter = previous_alert_counter
        self.alerts = self.alert_manager.alerts
        self.options: dict[str, dict] = {}
        self.last_optimized: dict[str, float] = {}
        self.option_sets: dict[str, tuple] = {}
        self.operator_restrictions: set[str] = set()
        self.pinger = Pinger(self.classifier)
        self.pinger.counter = previous_detection_counter
        self.detections = self.pinger.detections
        self.images = self.pinger.images
        self.disaster = DisasterSurvey(self.zones)
        self.zone_statuses = {zid: {"id": zid, "state": "unsurveyed" if mode == "disaster" else "open",
                                     "coverage": 0.0} for zid in self.zones.polygons}
        self.reopen_plan = self.disaster.reopen(self.zone_statuses) if mode == "disaster" else None

    def set_mode(self, mode, t):
        if mode not in {"security", "disaster"}:
            raise ValueError("mode must be security or disaster")
        if mode == self.mode:
            return []
        self.mode = mode
        self.disaster.reset()
        events = [("mode_changed", {"mode": mode})]
        for zid, status in self.zone_statuses.items():
            desired = "restricted" if zid in self.operator_restrictions else (
                "unsurveyed" if mode == "disaster" else "open")
            status["coverage"] = 0.0
            if status["state"] != desired:
                status["state"] = desired
                events.append(("zone_changed", {"zone_id": zid, "state": desired}))
        self.reopen_plan = self.disaster.reopen(self.zone_statuses) if mode == "disaster" else None
        if self.reopen_plan is not None:
            events.append(("reopen_plan", self.reopen_plan.copy()))
        events.append(AlertManager.log(t, f"切换至 {mode} 模式"))
        return events

    def step(self, tracks, world, dt):
        events = []
        if world.mode != self.mode:
            events.extend(self.set_mode(world.mode, world.t))
        live_ids = {tr["id"] for tr in tracks}
        events.extend(self.alert_manager.remove_missing(live_ids, world.t))
        for tid in set(self.risk.first_seen)-live_ids:
            self.risk.first_seen.pop(tid, None)
        for tr in tracks:
            score = self.risk.score(tr, world.t)
            events.extend(self.alert_manager.update(tr, score, world.t,
                                                   skip=self.mode == "disaster" and tr.get("cls") == "debris"))
        events.extend(self.pinger.step(tracks, world))
        if self.mode == "disaster":
            generated = self.disaster.step(world, tracks, dt, self.zone_statuses,
                                           self.operator_restrictions, self.pinger)
            events.extend(generated)
            if any(name == "zone_changed" for name, _ in generated):
                self.reopen_plan = self.disaster.reopen(self.zone_statuses)
                events.append(("reopen_plan", self.reopen_plan.copy()))
        tracks_by_id = {tr["id"]: tr for tr in tracks}
        for aid, alert in self.alerts.items():
            if alert["level"] != 3:
                continue
            if world.t-self.last_optimized.get(aid, -float("inf")) < config.OPTIMIZE_EVERY_S:
                continue
            data = self.optimizer.generate(tracks_by_id[alert["track_id"]], alert)
            signature = tuple((o["id"], tuple(o["zones_closed"]), tuple(o["speed_limit_zones"]))
                              for o in data["options"])
            self.options[aid] = data
            self.last_optimized[aid] = world.t
            alert["options_ready"] = True
            if self.option_sets.get(aid) != signature:
                self.option_sets[aid] = signature
                events.append(("options_ready", data))
        for mapping in (self.options, self.last_optimized, self.option_sets):
            for aid in set(mapping)-set(self.alerts):
                mapping.pop(aid, None)
        return events

    def approve(self, alert_id, option_id, action, operator, t):
        if action not in {"approve", "reject"}:
            raise ValueError("decision action must be approve or reject")
        if alert_id not in self.alerts or alert_id not in self.options:
            raise ValueError("alert or options no longer available")
        if self.alerts[alert_id]["level"] != 3:
            raise ValueError("only a current level-3 alert can accept a response decision")
        option = next((o for o in self.options[alert_id]["options"] if o["id"] == option_id), None)
        if option is None:
            raise ValueError("option is not available for this alert")
        if not isinstance(operator, str) or not operator.strip():
            raise ValueError("operator must be a nonempty string")
        events = []
        if action == "approve":
            events.append(("decision", {"alert_id": alert_id, "option_id": option_id,
                                        "action": action, "operator": operator}))
            for zid in option["zones_closed"]:
                self.operator_restrictions.add(zid)
                if self.zone_statuses[zid]["state"] != "restricted":
                    self.zone_statuses[zid]["state"] = "restricted"
                    events.append(("zone_changed", {"zone_id": zid, "state": "restricted"}))
            if self.mode == "disaster":
                self.reopen_plan = self.disaster.reopen(self.zone_statuses)
                events.append(("reopen_plan", self.reopen_plan.copy()))
        events.append(AlertManager.log(t, f"{operator} {action} {alert_id}/{option_id}", source="operator"))
        return events


__all__ = ["DecisionEngine", "Zones", "RiskScorer", "AlertManager", "Optimizer", "DisasterSurvey"]
