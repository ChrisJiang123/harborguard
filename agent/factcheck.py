"""RecommendationDraft 的确定性事实检查。

这里只拒绝能从上下文明确证明错误的断言，或任务书明确要求但缺失的字段语义。
任意自然语言事实的完全验证超出确定性规则能力，调用方必须公开这一局限。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .schemas import RecommendationDraft

FACT_CHECK_SCOPE = (
    "确定性检查仅覆盖浮标离线/覆盖数量、识别置信度、方案风险与延误、"
    "方案选择、recommended_option_id 及任务书规定的证据不足条件；"
    "未宣称验证全部自由文本事实。"
)

_CLAUSE_SPLIT = re.compile(r"[。；;！!？?\n]+")
_BUOY_ID = re.compile(r"(?<![A-Za-z0-9])B\d+(?![A-Za-z0-9])", re.IGNORECASE)
_UNKNOWN = re.compile(r"未知|待核实|待确认|无法确认|数据缺失|未提供")


@dataclass(frozen=True)
class SelectionCheck:
    task_rule_option_id: str | None
    ranked_option_id: str | None
    conflict: bool
    computable: bool


@dataclass
class FactCheckResult:
    errors: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=lambda: [FACT_CHECK_SCOPE])
    selection: SelectionCheck | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def security_selection(context: dict) -> SelectionCheck:
    """分别计算任务书规则和后端 ranked 首项，不掩盖二者差异。"""
    options = [o for o in context.get("options", []) if isinstance(o, dict) and o.get("id")]
    by_id = {o["id"]: o for o in options}
    ranked = [oid for oid in context.get("ranked", []) if oid in by_id]
    ranked_id = ranked[0] if ranked else None
    if not options:
        return SelectionCheck(None, ranked_id, False, True)

    metrics: list[tuple[int, dict, float, float]] = []
    for index, option in enumerate(options):
        risk = _number(option.get("residual_risk"))
        delay = _number(option.get("delay_vessel_hours"))
        if risk is None or delay is None:
            return SelectionCheck(None, ranked_id, False, False)
        metrics.append((index, option, risk, delay))
    acceptable = [entry for entry in metrics if entry[2] <= 0.2]
    if acceptable:
        chosen = min(acceptable, key=lambda entry: (entry[3], entry[0]))
    else:
        chosen = min(metrics, key=lambda entry: (entry[2], entry[0]))
    task_id = chosen[1]["id"]
    return SelectionCheck(task_id, ranked_id, ranked_id is not None and ranked_id != task_id, True)


def _clauses(draft: RecommendationDraft) -> list[str]:
    text = "。".join([draft.summary, draft.explanation, *draft.uncertainties])
    return [part.strip() for part in _CLAUSE_SPLIT.split(text) if part.strip()]


def _offline_claim(clause: str) -> tuple[str, int | None, set[str]] | None:
    mentioned_ids = {match.upper() for match in _BUOY_ID.findall(clause)}
    if not (
        ("浮标" in clause and "离线" in clause)
        or ("浮标" in clause and "在线" in clause)
        or (mentioned_ids and ("离线" in clause or "在线" in clause))
    ):
        return None
    if _UNKNOWN.search(clause):
        return ("unknown", None, set())
    if mentioned_ids and (
        ("在线" in clause and "离线" not in clause)
        or re.search(r"(?:未|没有|并未|不是)\s*离线", clause)
    ):
        return ("online_ids", None, mentioned_ids)
    negative = bool(
        re.search(r"(?:没有|无|不存在|未发现|未检测到|0\s*个)[^。；]{0,12}浮标[^。；]{0,8}离线", clause)
        or re.search(r"(?:没有|无|不存在|未发现|未检测到)[^。；]{0,8}离线浮标", clause)
        or re.search(r"浮标[^。；]{0,8}(?:没有|无|不存在)[^。；]{0,6}离线", clause)
        or re.search(r"离线浮标(?:数量|数)?\s*(?:为|是|=|：|:)?\s*0\s*个?", clause)
        or re.search(r"(?:全部|所有|均|全都)[^。；]{0,8}浮标[^。；]{0,8}(?:在线|正常)", clause)
        or re.search(r"浮标[^。；]{0,8}(?:全部|均|全都)[^。；]{0,8}(?:在线|正常)", clause)
    )
    if negative:
        return ("none", 0, set())
    if "离线" not in clause:
        return None
    count = None
    for pattern in (
        r"离线\s*(\d+)\s*个",
        r"(\d+)\s*个[^。；]{0,8}浮标[^。；]{0,8}离线",
        r"浮标[^。；]{0,8}离线[^。；]{0,4}(\d+)\s*个",
    ):
        match = re.search(pattern, clause)
        if match:
            count = int(match.group(1))
            break
    return ("some", count, mentioned_ids)


def _check_offline(draft: RecommendationDraft, context: dict, result: FactCheckResult) -> bool:
    buoys = context.get("buoys")
    known = isinstance(buoys, dict) and isinstance(buoys.get("down"), list)
    down = set(buoys.get("down", [])) if known else set()
    claims = [(clause, _offline_claim(clause)) for clause in _clauses(draft)]
    claims = [(clause, claim) for clause, claim in claims if claim is not None]
    for clause, claim in claims:
        kind, count, ids = claim
        if kind == "unknown":
            continue
        if not known:
            result.errors.append(f"浮标状态缺失却作出确定断言：{clause[:80]}")
        elif kind == "online_ids" and ids & down:
            result.errors.append(f"声称 {sorted(ids & down)} 在线，但上下文标记为离线")
        elif kind == "none" and down:
            result.errors.append(f"声称无浮标离线，但上下文离线为 {sorted(down)}")
        elif kind == "some" and not down:
            result.errors.append(f"声称存在浮标离线，但上下文离线列表为空：{clause[:80]}")
        elif kind == "some" and down:
            # “B4 离线”是可验证的单项事实，并不等于声称离线总数未知或为零。
            # 只有显式写出数量时才把该句视为总量陈述；完整总量与全部 ID
            # 仍由下方 uncertainties 的强制规则保证。
            if count is not None and count != len(down):
                result.errors.append(f"浮标离线数量 {count!r} 与上下文 {len(down)} 不一致")
            if ids - down or (count is not None and ids != down):
                result.errors.append(f"浮标离线 ID {sorted(ids)} 与上下文 {sorted(down)} 不一致")

    weak = False
    if not known:
        weak = True
        if not any(_UNKNOWN.search(u) and "浮标" in u for u in draft.uncertainties):
            result.errors.append("浮标状态缺失时必须在 uncertainties 标明未知")
    elif down:
        weak = True
        uncertainty_claims = [_offline_claim(u) for u in draft.uncertainties]
        if not any(c and c[0] == "some" and c[1] == len(down) and c[2] == down for c in uncertainty_claims):
            result.errors.append("有浮标离线时，uncertainties 必须准确写明数量和全部 ID")
    return weak


def _check_covering(draft: RecommendationDraft, context: dict, result: FactCheckResult) -> bool:
    buoys = context.get("buoys")
    known = isinstance(buoys, dict) and isinstance(buoys.get("covering_track"), list)
    actual = len(buoys["covering_track"]) if known else None
    patterns = (
        r"(?:仅|只有|共|有|约)?\s*(\d+)\s*个\s*浮标(?:提供)?覆盖",
        r"浮标覆盖(?:数量|数)?\s*(?:为|是|共|有|=|：|:)?\s*(\d+)",
    )
    for clause in _clauses(draft):
        if _UNKNOWN.search(clause):
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                claimed = int(match.group(1))
                if actual is None:
                    result.errors.append(f"覆盖数据缺失却声称有 {claimed} 个浮标覆盖")
                elif claimed != actual:
                    result.errors.append(f"覆盖浮标数量 {claimed} 与上下文 {actual} 不一致")

    if not known:
        if context.get("kind") == "security":
            if not any("覆盖" in u and _UNKNOWN.search(u) for u in draft.uncertainties):
                result.errors.append("覆盖数据缺失时必须在 uncertainties 标明未知")
            return True
        return False
    if context.get("kind") == "security" and actual <= 1:
        if not any("覆盖" in u and re.search(r"不足|有限|薄弱|仅|只有|0\s*个", u) for u in draft.uncertainties):
            result.errors.append("覆盖浮标不超过 1 个时必须在 uncertainties 说明证据不足")
        return True
    return False


def _check_confidence(draft: RecommendationDraft, context: dict, result: FactCheckResult) -> bool:
    if context.get("kind") != "security":
        return False
    track = context.get("track")
    actual = _number(track.get("conf")) if isinstance(track, dict) else None
    for clause in _clauses(draft):
        if "置信度" not in clause or _UNKNOWN.search(clause):
            continue
        for match in re.finditer(r"置信度\s*(?:为|是|约|=|：|:)?\s*([01](?:\.\d+)?)", clause):
            claimed = float(match.group(1))
            if actual is None:
                result.errors.append(f"识别置信度缺失却声称为 {claimed:g}")
            elif abs(claimed - actual) > 0.011:
                result.errors.append(f"识别置信度 {claimed:g} 与上下文 {actual:g} 不一致")
        for match in re.finditer(r"置信度\s*(不低于|低于|高于|不高于)\s*([01](?:\.\d+)?)", clause):
            relation, threshold = match.group(1), float(match.group(2))
            if actual is None:
                result.errors.append(f"识别置信度缺失却声称{relation}{threshold:g}")
            else:
                valid = {
                    "不低于": actual >= threshold,
                    "低于": actual < threshold,
                    "高于": actual > threshold,
                    "不高于": actual <= threshold,
                }[relation]
                if not valid:
                    result.errors.append(f"置信度关系“{relation}{threshold:g}”与上下文 {actual:g} 矛盾")
        low_claim = bool(re.search(r"置信度[^。；]{0,5}(?:较低|偏低|不足)|低置信度", clause))
        low_claim = low_claim and not bool(re.search(r"置信度\s*不低", clause))
        high_claim = bool(re.search(r"置信度[^。；]{0,5}(?:较高|偏高)", clause))
        if actual is None and (low_claim or high_claim):
            result.errors.append("识别置信度缺失却作出高低判断")
        elif actual is not None and actual >= 0.6 and low_claim:
            result.errors.append(f"声称识别置信度低，但上下文为 {actual:g}（不低于 0.6）")
        elif actual is not None and actual < 0.6 and high_claim:
            result.errors.append(f"声称识别置信度高，但上下文为 {actual:g}（低于 0.6）")

    if actual is None:
        if not any("置信度" in u and _UNKNOWN.search(u) for u in draft.uncertainties):
            result.errors.append("识别置信度缺失时必须在 uncertainties 标明未知")
        return True
    if actual < 0.6:
        if not any("置信度" in u and re.search(r"低|不足|小于|低于", u) for u in draft.uncertainties):
            result.errors.append("识别置信度低于 0.6 时必须在 uncertainties 说明")
        return True
    return False


def _matches_known(value: float, known: list[float]) -> bool:
    return any(abs(value - expected) <= 0.011 for expected in known)


def _metric_candidates(clause: str, start: int, options: list[dict], selected: str | None) -> list[dict]:
    mentioned: list[tuple[int, dict]] = []
    for option in options:
        for token in (option.get("id"), option.get("label")):
            if not token:
                continue
            position = clause.rfind(str(token), 0, start)
            if position >= 0:
                mentioned.append((position, option))
    if mentioned:
        return [max(mentioned, key=lambda item: item[0])[1]]
    if selected:
        chosen = next((option for option in options if option.get("id") == selected), None)
        if chosen is not None:
            return [chosen]
    return options


def _check_option_metrics(draft: RecommendationDraft, context: dict, result: FactCheckResult) -> None:
    options = [o for o in context.get("options", []) if isinstance(o, dict)]
    for clause in _clauses(draft):
        for match in re.finditer(
            r"残余风险\s*(?:为|是|约|=|：|:)?\s*(\d+(?:\.\d+)?)\s*(%?)", clause
        ):
            value = float(match.group(1)) / (100 if match.group(2) else 1)
            candidates = _metric_candidates(clause, match.start(), options, draft.recommended_option_id)
            risks = [number for option in candidates if (number := _number(option.get("residual_risk"))) is not None]
            if not risks:
                result.errors.append(f"方案风险数据缺失却声称残余风险为 {value:g}")
            elif not _matches_known(value, risks):
                result.errors.append(f"残余风险 {value:g} 与所述方案上下文事实不一致")
        for match in re.finditer(
            r"延误(?:船舶)?\s*(?:为|是|约|=|：|:)?\s*(\d+(?:\.\d+)?)\s*(?:船时|小时)", clause
        ):
            value = float(match.group(1))
            candidates = _metric_candidates(clause, match.start(), options, draft.recommended_option_id)
            delays = [number for option in candidates if (number := _number(option.get("delay_vessel_hours"))) is not None]
            if not delays:
                result.errors.append(f"方案延误数据缺失却声称延误为 {value:g}")
            elif not _matches_known(value, delays):
                result.errors.append(f"方案延误 {value:g} 与所述方案上下文事实不一致")


def _check_selection(draft: RecommendationDraft, context: dict, result: FactCheckResult) -> None:
    kind = context.get("kind")
    options = context.get("options", []) or []
    if kind in {"disaster", "buoy"}:
        if draft.recommended_option_id is not None:
            result.errors.append(f"{kind} 建议的 recommended_option_id 必须为 null")
        return
    if kind != "security":
        return
    selection = security_selection(context)
    result.selection = selection
    if not options:
        if draft.recommended_option_id is not None:
            result.errors.append("没有 options 时 recommended_option_id 必须为 null")
        return
    if selection.computable and draft.recommended_option_id != selection.task_rule_option_id:
        result.errors.append(
            f"方案选择不符合任务书规则：应为 {selection.task_rule_option_id}，"
            f"实际为 {draft.recommended_option_id}"
        )
    if not selection.computable:
        result.limitations.append("部分方案缺少风险或延误，无法确定性复算任务书选择规则。")
    if selection.conflict:
        described = any(
            selection.task_rule_option_id in u
            and selection.ranked_option_id in u
            and re.search(r"规则|排序|ranked|差异|冲突", u, re.IGNORECASE)
            for u in draft.uncertainties
        )
        if not described:
            result.errors.append(
                f"任务书规则 {selection.task_rule_option_id} 与后端 ranked 首项 "
                f"{selection.ranked_option_id} 不同，必须在 uncertainties 报告差异"
            )


def check_draft_facts(draft: RecommendationDraft, context: dict) -> FactCheckResult:
    """检查能从结构化上下文明确判断的事实和任务规则。"""
    result = FactCheckResult()
    _check_selection(draft, context, result)
    _check_option_metrics(draft, context, result)
    weak = _check_offline(draft, context, result)
    weak = _check_covering(draft, context, result) or weak
    weak = _check_confidence(draft, context, result) or weak
    if weak and draft.confidence != "low":
        result.errors.append("存在任务书定义的证据不足条件时 confidence 必须为 low")
    return result


def fact_snapshot(context: dict) -> dict:
    """失败样例只保留校验所需结构化事实，不保存日志、坐标或凭证。"""
    track = context.get("track") or {}
    buoys = context.get("buoys") or {}
    return {
        "kind": context.get("kind"),
        "track_conf": track.get("conf") if "conf" in track else None,
        "buoys": {
            key: buoys.get(key) for key in ("ok", "down", "covering_track") if key in buoys
        },
        "options": [
            {key: option.get(key) for key in ("id", "delay_vessel_hours", "residual_risk") if key in option}
            for option in context.get("options", [])
        ],
        "ranked": context.get("ranked", []),
        "reopen_plan": context.get("reopen_plan"),
        "zones": [
            {key: zone.get(key) for key in ("id", "state", "coverage") if key in zone}
            for zone in context.get("zones", [])
        ],
        "coverage_impact": context.get("coverage_impact"),
    }
