"""C3 final template fallback: no model; recommend the first valid ranked option within two seconds.
With no valid option use null and state what the operator must check. Report insufficient coverage,
confidence <0.6, offline buoys or residual risk >0.2 in uncertainties and lower confidence.
Interpret/recommend only; never act or change alert levels. model is always template.
"""


from __future__ import annotations

from .factcheck import security_selection
from .schemas import RecommendationDraft, clip


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _offline_uncertainty(buoys: dict) -> tuple[list[str], bool]:
    if "down" not in buoys or not isinstance(buoys.get("down"), list):
        return ["浮标状态数据缺失，离线情况未知"], True
    down = list(buoys["down"])
    if not down:
        return [], False
    return [clip(f"浮标离线 {len(down)} 个:{','.join(down)}", 40)], True


def _generate_security_zh(context: dict) -> RecommendationDraft:
    alert = context.get("alert") or {}
    track = context.get("track") or {}
    options = context.get("options", []) or []
    ranked = context.get("ranked", []) or []
    buoys = context.get("buoys", {}) or {}
    covering_known = isinstance(buoys.get("covering_track"), list)
    covering = list(buoys["covering_track"]) if covering_known else []
    conf = _number(track.get("conf"))

    by_id = {o["id"]: o for o in options}
    valid_ranked = [oid for oid in ranked if oid in by_id]
    selection = security_selection(context)

    uncertainties, offline_weak = _offline_uncertainty(buoys)
    if not covering_known:
        uncertainties.append("浮标覆盖数据缺失，覆盖情况未知")
    elif len(covering) <= 1:
        uncertainties.append(f"仅 {len(covering)} 个浮标覆盖，定位证据不足")
    if conf is None:
        uncertainties.append("识别置信度数据缺失，当前未知")
    elif conf < 0.6:
        uncertainties.append(f"识别置信度 {conf:.2f}，低于 0.6")

    if selection.conflict:
        uncertainties.append(
            clip(
                f"任务规则 {selection.task_rule_option_id} 与后端排序 {selection.ranked_option_id} 存在差异",
                40,
            )
        )

    if not options:
        uncertainties.append("可用方案列表为空或均不在 ranked 中")
        summary = clip(f"暂无可用处置方案，建议核实{track.get('cls', '目标')}意图并复核警报", 60)
        risk = _number(alert.get("risk"))
        risk_text = f"，综合风险 {risk:.2f}" if risk is not None else "，综合风险未知"
        explanation = f"警报 {alert.get('id')}（{alert.get('level')} 级{risk_text}）暂无可用处置方案。"
        explanation += "建议值班员核实目标意图、确认浮标覆盖与识别置信度，方案生成后再行处置。"
        evidence = [i for i in (alert.get("id"), track.get("id")) if i]
        return RecommendationDraft(
            summary=clip(summary, 60),
            explanation=clip(explanation, 300),
            recommended_option_id=None,
            evidence_ids=[e for e in evidence if e][:8],
            uncertainties=uncertainties[:6],
            confidence="low",
        )

    option_id = selection.task_rule_option_id or (valid_ranked[0] if valid_ranked else None)
    if option_id is None or option_id not in by_id:
        uncertainties.append("方案风险或延误数据缺失，无法复算选择规则")
        evidence = [i for i in (alert.get("id"), track.get("id")) if i]
        return RecommendationDraft(
            summary="方案指标不完整，建议值班员核实后选择",
            explanation="现有方案缺少可确定核对的风险或延误数据，无法按任务书规则选出方案。最终处置由值班员决定。",
            recommended_option_id=None,
            evidence_ids=evidence,
            uncertainties=[clip(u, 40) for u in uncertainties[:6]],
            confidence="low",
        )
    opt = by_id[option_id]
    residual = _number(opt.get("residual_risk"))
    delay = _number(opt.get("delay_vessel_hours"))
    if residual is not None and residual > 0.2:
        uncertainties.append(f"推荐方案残余风险 {residual:.2f}，高于 0.2")

    metrics = []
    if residual is not None:
        metrics.append(f"残余风险 {residual:.2f}")
    if delay is not None:
        metrics.append(f"延误 {delay:.1f} 船时")
    summary = clip(f"推荐 {opt.get('label', option_id)}" + (f"：{'，'.join(metrics)}" if metrics else ""), 60)
    top_key, top_val = _dominant_factor(alert.get("breakdown") or {})
    risk = _number(alert.get("risk"))
    explanation = f"警报 {alert.get('id')}（{alert.get('level')} 级"
    explanation += f"，风险 {risk:.2f}" if risk is not None else "，风险未知"
    if top_val is not None:
        explanation += f"，主导因素 {top_key} {top_val:.2f}"
    explanation += "）。"
    explanation += f"目标 {track.get('id')}（{track.get('cls')}"
    explanation += f"，置信度 {conf:.2f}" if conf is not None else "，置信度未知"
    explanation += f"，{len(covering)} 个浮标覆盖" if covering_known else "，覆盖数量未知"
    explanation += "）。"
    explanation += f"按任务书规则推荐方案 {option_id}：{opt.get('label')}"
    if delay is not None:
        explanation += f"，延误 {delay:.1f} 船时"
    if residual is not None:
        explanation += f"，残余风险 {residual:.2f}"
    explanation += "。最终处置由值班员决定。"
    evidence_ids = [i for i in (alert.get("id"), track.get("id")) if i]
    evidence_ids += [d["id"] for d in context.get("detections", []) if d.get("id")]
    evidence_ids += covering

    weak = offline_weak or not covering_known or len(covering) <= 1 or conf is None or conf < 0.6
    confidence = "low" if weak else ("high" if residual is not None and residual <= 0.2 else "medium")
    return RecommendationDraft(
        summary=summary,
        explanation=clip(explanation, 300),
        recommended_option_id=option_id,
        evidence_ids=list(dict.fromkeys(evidence_ids))[:8],
        uncertainties=[clip(u, 40) for u in uncertainties[:6]],
        confidence=confidence,
    )


def _generate_disaster_zh(context: dict) -> RecommendationDraft:
    plan = context.get("reopen_plan") or {}
    route = list(plan.get("route_zone_ids", []))
    berths = list(plan.get("reopen_berth_zone_ids", []))
    unsurveyed = list(plan.get("unsurveyed_zone_ids", []))
    blocked = list(plan.get("blocked_zone_ids", []))
    uncertainties, weak = _offline_uncertainty(context.get("buoys") or {})
    if unsurveyed:
        uncertainties.append(clip(f"待人工勘测分区：{','.join(unsurveyed)}", 40))
    if not plan:
        uncertainties.append("复航计划数据缺失，当前计划未知")
        weak = True
    summary = f"可先复航泊位 {len(berths)} 个，待勘测分区 {len(unsurveyed)} 个"
    explanation = f"可达航道分区：{','.join(route) or '无'}；可先复航泊位：{','.join(berths) or '无'}。"
    explanation += f"待人工勘测：{','.join(unsurveyed) or '无'}；阻塞分区：{','.join(blocked) or '无'}。"
    saved = _number(plan.get("est_hours_saved"))
    if saved is not None:
        explanation += f"计划估算节省 {saved:g} 小时。"
    explanation += "最终复航决定由值班员作出。"
    evidence = list(dict.fromkeys([*route, *berths, *unsurveyed, *blocked, *(context.get("buoys") or {}).get("down", [])]))
    return RecommendationDraft(
        summary=clip(summary, 60),
        explanation=clip(explanation, 300),
        recommended_option_id=None,
        evidence_ids=evidence,
        uncertainties=[clip(u, 40) for u in uncertainties[:6]],
        confidence="low" if weak else "high",
    )


def _generate_buoy_zh(context: dict) -> RecommendationDraft:
    buoy = context.get("buoy") or {}
    buoy_id = buoy.get("id")
    impact = context.get("coverage_impact") or {}
    affected = list(impact.get("affected_zone_ids", []))
    remaining = impact.get("remaining_ok_buoy_ids_by_zone") or {}
    uncertainties, weak = _offline_uncertainty(context.get("buoys") or {})
    summary = clip(f"浮标 {buoy_id} 状态异常，需核实量程相交分区覆盖", 60)
    explanation = (
        f"浮标 {buoy_id} 状态为 down；按其量程与分区几何相交计算，相关分区为 "
        f"{','.join(affected) or '无'}。"
    )
    uncovered = [zone_id for zone_id in affected if not remaining.get(zone_id)]
    if uncovered:
        explanation += f"其中 {','.join(uncovered)} 未发现其他在线浮标量程相交，建议人工补位或巡逻。"
    else:
        explanation += "相关分区仍有其他在线浮标量程相交，建议复核实际声学覆盖并安排巡逻。"
    evidence = [buoy_id, *affected]
    evidence += [bid for zone_id in affected for bid in remaining.get(zone_id, [])]
    return RecommendationDraft(
        summary=summary,
        explanation=clip(explanation, 300),
        recommended_option_id=None,
        evidence_ids=list(dict.fromkeys(i for i in evidence if i)),
        uncertainties=[clip(u, 40) for u in uncertainties[:6]],
        confidence="low" if weak or not affected else "medium",
    )


def generate_recommendation(context: dict) -> RecommendationDraft:
    kind = context.get("kind")
    if kind == "disaster":
        return generate_disaster(context)
    if kind == "buoy":
        return generate_buoy(context)
    return generate_security(context)


def _dominant_factor(breakdown: dict) -> tuple[str, float | None]:
    if not breakdown:
        return ("未知", None)
    values = {key: _number(value) for key, value in breakdown.items()}
    known = {key: value for key, value in values.items() if value is not None}
    if not known:
        return ("未知", None)
    key = max(known, key=known.get)
    return (key, known[key])


def _generate_answer_zh(question: str, *, track: dict | None, state: dict | None) -> str:
    """Template /ask answer: backend facts only, <=150 characters, model=template."""
    parts: list[str] = []
    if track:
        parts.append(
            f"航迹 {track.get('id')}（{track.get('cls')}）置信度 {float(track.get('conf', 0.0)):.2f}，"
            f"深度 {float(track.get('depth_m', 0.0)):.1f} 米，速度 {float(track.get('speed_mps', 0.0)):.1f} 米/秒"
        )
    else:
        parts.append("未找到指定航迹" if question else "当前无指定航迹")
    if state:
        alerts = state.get("alerts", []) or []
        if alerts:
            top = max(alerts, key=lambda a: a.get("level", 0))
            parts.append(
                f"当前 {len(alerts)} 条警报，最高 {top.get('level')} 级"
                f"（{top.get('id')}，风险 {float(top.get('risk', 0.0)):.2f}）"
            )
        else:
            parts.append(f"当前无警报（t={float(state.get('t', 0.0)):.0f} 秒）")
    parts.append("以上为后端实时事实，模板回答，最终判断由值班员作出")
    return clip("；".join(parts), 150)


def generate_security(context: dict) -> RecommendationDraft:
    from .language import language
    from .template_en import security
    return security(context) if language() == "en" else _generate_security_zh(context)


def generate_disaster(context: dict) -> RecommendationDraft:
    from .language import language
    from .template_en import disaster
    return disaster(context) if language() == "en" else _generate_disaster_zh(context)


def generate_buoy(context: dict) -> RecommendationDraft:
    from .language import language
    from .template_en import buoy
    return buoy(context) if language() == "en" else _generate_buoy_zh(context)


def generate_answer(question: str, *, track: dict | None, state: dict | None) -> str:
    from .language import language
    from .template_en import answer
    if language() == "en":
        return answer(question, track=track, state=state)
    return _generate_answer_zh(question, track=track, state=state)
