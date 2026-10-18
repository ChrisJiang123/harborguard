"""English deterministic fallback, using the same facts and selection rule as zh."""
from .factcheck import security_selection
from .language import CONTACT_NAMES, clip_field
from .schemas import RecommendationDraft, clip
from .template import _number


def _offline(buoys):
    if not isinstance(buoys.get("down"), list):
        return ["Buoy status unknown."], True
    down = buoys["down"]
    # Fits all B1–B10 IDs inside the unchanged 40-character transport cap.
    return ([f"{len(down)} down:{','.join(down)}"] if down else []), bool(down)


def _draft(summary, explanation, option, evidence, uncertainties, confidence):
    return RecommendationDraft(
        summary=clip_field(summary, "summary", "en"),
        explanation=clip_field(explanation, "explanation", "en"),
        recommended_option_id=option,
        evidence_ids=list(dict.fromkeys(i for i in evidence if i)),
        uncertainties=[clip_field(u, "uncertainties", "en") for u in uncertainties[:6]],
        confidence=confidence,
    )


def security(context):
    alert, track, buoys = (context.get(k) or {} for k in ("alert", "track", "buoys"))
    options = context.get("options") or []
    by_id = {o["id"]: o for o in options}
    selected = security_selection(context)
    uncertainties, weak = _offline(buoys)
    covering = buoys.get("covering_track")
    conf = _number(track.get("conf"))
    if not isinstance(covering, list):
        uncertainties.append("Buoy coverage unknown.")
        weak = True
    elif len(covering) <= 1:
        uncertainties.append(f"Only {len(covering)} buoy covers; evidence limited.")
        weak = True
    if conf is None:
        uncertainties.append("Identification confidence unknown.")
        weak = True
    elif conf < .6:
        uncertainties.append(f"Confidence {conf:.2f} below 0.6.")
        weak = True
    if selected.conflict:
        uncertainties.append(f"Rule {selected.task_rule_option_id}; ranked {selected.ranked_option_id} differ.")
    evidence = [alert.get("id"), track.get("id")]
    contact = CONTACT_NAMES.get(track.get("cls"), "unidentified contact")
    if not options:
        uncertainties.append("No options; verify contact intent.")
        return _draft(
            f"Verify {contact}; await options.",
            f"No options for alert {alert.get('id')}. Verify contact intent, buoy coverage and identification. "
            "The operator decides after options become available.",
            None, evidence, uncertainties, "low",
        )
    option_id = selected.task_rule_option_id
    if option_id not in by_id:
        uncertainties.append("Option risk or delay unknown.")
        return _draft("Verify incomplete option metrics.",
                      "Option risk or delay is unknown; a choice cannot be verified. The operator must review.",
                      None, evidence, uncertainties, "low")
    option = by_id[option_id]
    residual, delay = _number(option.get("residual_risk")), _number(option.get("delay_vessel_hours"))
    if residual > .2:
        uncertainties.append(f"Residual risk {residual:.2f} above 0.2.")
    risk = _number(alert.get("risk"))
    risk_text = f"risk {risk:.2f}" if risk is not None else "risk unknown"
    conf_text = f"confidence {conf:.2f}" if conf is not None else "confidence unknown"
    coverage_text = f"{len(covering)} buoys cover" if isinstance(covering, list) else "coverage unknown"
    explanation = (f"Alert {alert.get('id')} level {alert.get('level')}, {risk_text}. "
                   f"Contact {track.get('id')}: {contact}, {conf_text}; {coverage_text}. "
                   f"Recommend {option_id}: residual risk {residual:.2f}; delay {delay:.1f} hours. "
                   "Operator approval required.")
    evidence += [d["id"] for d in context.get("detections", []) if d.get("id")]
    evidence += covering if isinstance(covering, list) else []
    return _draft(f"Recommend {option_id}; risk {residual:.2f}; delay {delay:.1f} vh.",
                  explanation, option_id, list(dict.fromkeys(evidence))[:8], uncertainties,
                  "low" if weak else "high" if residual <= .2 else "medium")


def disaster(context):
    plan = context.get("reopen_plan") or {}
    route, berths, unsurveyed, blocked = (list(plan.get(k, [])) for k in
        ("route_zone_ids", "reopen_berth_zone_ids", "unsurveyed_zone_ids", "blocked_zone_ids"))
    uncertainties, weak = _offline(context.get("buoys") or {})
    if unsurveyed:
        uncertainties.append(f"{len(unsurveyed)} zones require a manual survey.")
    if not plan:
        uncertainties.append("Reopening plan unknown.")
        weak = True
    explanation = (f"Routes: {','.join(route) or 'none'}; berths: {','.join(berths) or 'none'}. "
                   f"Survey: {','.join(unsurveyed) or 'none'}; blocked: {','.join(blocked) or 'none'}. ")
    saved = _number(plan.get("est_hours_saved"))
    if saved is not None:
        explanation += f"Estimated saving: {saved:g} hours. "
    explanation += "The operator approves reopening."
    evidence = [*route, *berths, *unsurveyed, *blocked, *(context.get("buoys") or {}).get("down", [])]
    return _draft(f"Reopen {len(berths)} berths; survey {len(unsurveyed)} zones.",
                  explanation, None, evidence, uncertainties, "low" if weak else "high")


def buoy(context):
    buoy_id = (context.get("buoy") or {}).get("id")
    impact = context.get("coverage_impact") or {}
    affected = list(impact.get("affected_zone_ids", []))
    remaining = impact.get("remaining_ok_buoy_ids_by_zone") or {}
    uncertainties, weak = _offline(context.get("buoys") or {})
    uncovered = [z for z in affected if not remaining.get(z)]
    explanation = f"Buoy {buoy_id} is offline. Range overlaps: {','.join(affected) or 'none'}. "
    if uncovered:
        explanation += f"No other online buoy range intersects {','.join(uncovered)}. Arrange manual patrols."
    else:
        explanation += "Other online buoy ranges intersect these zones. Verify acoustic coverage and arrange patrols."
    evidence = [buoy_id, *affected, *(bid for z in affected for bid in remaining.get(z, []))]
    return _draft(f"Buoy {buoy_id} offline; verify coverage.", explanation, None, evidence,
                  uncertainties, "low" if weak or not affected else "medium")


def answer(question, *, track, state):
    parts = []
    if track:
        contact = CONTACT_NAMES.get(track.get("cls"), "unidentified contact")
        parts.append(f"Track {track.get('id')}: {contact}; confidence {float(track.get('conf', 0)):.2f}")
    else:
        parts.append("No matching track" if question else "No selected track")
    if state:
        alerts = state.get("alerts") or []
        parts.append(f"{len(alerts)} alerts; highest level {max((a.get('level', 0) for a in alerts), default=0)}")
    parts.append("Live backend facts; template answer. Operator decides.")
    return clip(". ".join(parts), 150)
