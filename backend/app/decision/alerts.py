"""Alert lifecycle with immediate escalation and continuous downgrade hysteresis."""
from __future__ import annotations

from copy import deepcopy

from .. import config


def raw_level(track: dict, score: dict) -> int:
    if track.get("cls") == "vessel":
        return 0
    risk = score["risk"]
    near = score["distance_m"] <= config.L3_CORE_M
    eta = score["eta_s"]
    if risk >= config.L3_R and (near or eta is not None and eta < config.L3_ETA_S):
        return 3 if track.get("status") == "confirmed" else 2
    if risk >= config.L2_R or score["breakdown"]["B"] > config.BEHAVIOR_LEVEL2_THRESHOLD:
        return 2
    return 1 if risk >= config.L1_R else 0


class AlertManager:
    def __init__(self):
        self.alerts: dict[str, dict] = {}
        self.by_track: dict[str, str] = {}
        self.levels: dict[str, int] = {}
        self.below_since: dict[str, float] = {}
        self.counter = 0

    @staticmethod
    def log(t: float, text: str, level: str = "info", source: str = "decision") -> tuple:
        return "log", {"log": {"t": t, "level": level, "source": source, "text": text}}

    def update(self, track: dict, score: dict, t: float, skip: bool = False) -> list[tuple]:
        tid = track["id"]
        previous = self.levels.get(tid, 0)
        desired = 0 if skip else raw_level(track, score)
        if desired >= previous:
            level = desired
            self.below_since.pop(tid, None)
        elif skip or track.get("cls") == "vessel":
            level = 0
            self.below_since.pop(tid, None)
        else:
            self.below_since.setdefault(tid, t)
            level = desired if t-self.below_since[tid] >= config.HYSTERESIS_S else previous
            if level != previous:
                self.below_since.pop(tid, None)
        self.levels[tid] = level
        track.update(level=level, risk=score["risk"])
        events = []
        if level == 0:
            if tid in self.by_track:
                aid = self.by_track.pop(tid)
                self.alerts.pop(aid, None)
                events.extend([("alert_cleared", {"alert_id": aid}), self.log(t, f"Alert {aid} cleared")])
            return events
        if tid not in self.by_track:
            self.counter += 1
            aid = f"A{self.counter}"
            self.by_track[tid] = aid
            self.alerts[aid] = {"id": aid, "track_id": tid, "raised_t": t, "options_ready": False}
        aid = self.by_track[tid]
        alert = self.alerts[aid]
        alert.update(score, level=level, updated_t=t)
        if previous == 0:
            events.append(("alert_raised", {"alert": deepcopy(alert)}))
        elif previous != level:
            events.append(("alert_changed", {"alert": deepcopy(alert), "from_level": previous, "to_level": level}))
        if previous != level:
            events.append(self.log(t, f"Track {tid} alert level {previous} -> {level}", "critical" if level == 3 else "info"))
        return events

    def remove_missing(self, live_ids: set[str], t: float) -> list[tuple]:
        events = []
        for tid in list(self.levels):
            if tid in live_ids:
                continue
            self.levels.pop(tid, None)
            self.below_since.pop(tid, None)
            aid = self.by_track.pop(tid, None)
            if aid:
                self.alerts.pop(aid, None)
                events.extend([("alert_cleared", {"alert_id": aid}), self.log(t, f"Track {tid} lost; alert {aid} cleared")])
        return events
