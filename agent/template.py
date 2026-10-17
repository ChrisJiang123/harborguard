"""模板建议（C3 末级兜底）：不用模型，按 ranked 首个有效方案拼建议，2 秒内返回。

规则（任务书 C3 系统提示词的模板化表达，与后续 LLM 同一上下文）：
- 推荐有效 ranked 中的首个方案；无可用方案时 recommended_option_id = null，
  说明值班员应核实什么；
- 证据不足（仅 1 个浮标覆盖、识别置信度 < 0.6、有浮标离线、残余风险 > 0.2）
  写入 uncertainties 并降低 confidence；
- 只解读和推荐，不改警报等级、不执行任何操作；model 恒为 template。
"""

from __future__ import annotations

from .schemas import RecommendationDraft, clip


def generate_security(context: dict) -> RecommendationDraft:
    alert = context.get("alert") or {}
    track = context.get("track") or {}
    options = context.get("options", []) or []
    ranked = context.get("ranked", []) or []
    buoys = context.get("buoys", {}) or {}
    covering = list(buoys.get("covering_track", []))
    down = list(buoys.get("down", []))
    conf = float(track.get("conf", 0.0) or 0.0)

    by_id = {o["id"]: o for o in options}
    valid_ranked = [oid for oid in ranked if oid in by_id]

    uncertainties: list[str] = []
    if len(covering) <= 1:
        uncertainties.append(f"仅 {len(covering)} 个浮标覆盖，定位证据不足")
    if conf < 0.6:
        uncertainties.append(f"识别置信度 {conf:.2f}，低于 0.6")
    if down:
        uncertainties.append(f"浮标离线 {len(down)} 个（{','.join(down[:3])}）")

    if not valid_ranked:
        uncertainties.append("可用方案列表为空或均不在 ranked 中")
        summary = clip(f"暂无可用处置方案，建议核实{track.get('cls', '目标')}意图并复核警报", 60)
        explanation = (
            f"警报 {alert.get('id')}（{alert.get('level')} 级，综合风险 "
            f"{float(alert.get('risk', 0.0)):.2f}）暂无可用处置方案。"
            "建议值班员核实目标意图、确认浮标覆盖与识别置信度，方案生成后再行处置。"
        )
        evidence = [i for i in (alert.get("id"), track.get("id")) if i]
        return RecommendationDraft(
            summary=clip(summary, 60),
            explanation=clip(explanation, 300),
            recommended_option_id=None,
            evidence_ids=[e for e in evidence if e][:8],
            uncertainties=uncertainties[:6],
            confidence="low",
        )

    option_id = valid_ranked[0]
    opt = by_id[option_id]
    residual = float(opt.get("residual_risk", 0.0))
    delay = float(opt.get("delay_vessel_hours", 0.0))
    if residual > 0.2:
        uncertainties.append(f"推荐方案残余风险 {residual:.2f}，高于 0.2")

    summary = clip(
        f"推荐 {opt.get('label', option_id)}：残余风险 {residual:.2f}，延误 {delay:.1f} 船时",
        60,
    )
    top_key, top_val = _dominant_factor(alert.get("breakdown") or {})
    explanation = (
        f"警报 {alert.get('id')}（{alert.get('level')} 级，风险 {float(alert.get('risk', 0.0)):.2f}，"
        f"主导因素 {top_key} {top_val:.2f}）。"
        f"目标 {track.get('id')}（{track.get('cls')}，置信度 {conf:.2f}，"
        f"速度 {float(track.get('speed_mps', 0.0)):.1f} m/s，深度 {float(track.get('depth_m', 0.0)):.1f} m，"
        f"{len(covering)} 个浮标覆盖）。"
        f"按排序推荐方案 {option_id}：{opt.get('label')}，关闭 "
        f"{opt.get('zones_closed_count', len(opt.get('zones_closed', [])))} 个分区，"
        f"影响 {opt.get('vessels_affected', 0)} 艘船、延误 {delay:.1f} 船时，残余风险 {residual:.2f}。"
        "最终处置由值班员决定。"
    )
    evidence_ids = [i for i in (alert.get("id"), track.get("id")) if i]
    evidence_ids += [d["id"] for d in context.get("detections", []) if d.get("id")]
    evidence_ids += covering

    weak = len(covering) <= 1 or conf < 0.6 or bool(down)
    confidence = "low" if weak else ("high" if residual <= 0.2 else "medium")
    return RecommendationDraft(
        summary=summary,
        explanation=clip(explanation, 300),
        recommended_option_id=option_id,
        evidence_ids=list(dict.fromkeys(evidence_ids))[:8],
        uncertainties=uncertainties[:6],
        confidence=confidence,
    )


def _dominant_factor(breakdown: dict) -> tuple[str, float]:
    if not breakdown:
        return ("未知", 0.0)
    key = max(breakdown, key=lambda k: float(breakdown.get(k, 0.0) or 0.0))
    return (key, float(breakdown.get(key, 0.0) or 0.0))


def generate_answer(question: str, *, track: dict | None, state: dict | None) -> str:
    """/ask 的模板回答：只引用后端事实数字，≤150 字，model=template。"""
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
