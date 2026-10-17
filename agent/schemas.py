"""Agent 模型与双重校验（C3 阶段一）。

- RecommendationDraft：生成侧草案（云端/本地/模板三处同构）。
- Recommendation：契约 v1 的完整建议（POST /api/recommendations 请求体）。
- normalize_draft：超长字段截断、去重。
- validate_draft：**上下文真实 ID** 校验（evidence_ids / recommended_option_id），
  与后端 422 校验形成双保险；禁改警报等级、禁调 /api/decision 由实现保证。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_SUMMARY = 60
MAX_EXPLANATION = 300
MAX_UNCERTAINTY = 40


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RecommendationDraft(StrictModel):
    summary: str = ""
    explanation: str = ""
    recommended_option_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"


class Recommendation(StrictModel):
    id: str
    kind: Literal["security", "disaster", "buoy"]
    alert_id: str | None
    model: Literal["cloud", "local", "template"]
    summary: Annotated[str, Field(max_length=MAX_SUMMARY)]
    explanation: Annotated[str, Field(max_length=MAX_EXPLANATION)]
    recommended_option_id: str | None
    evidence_ids: list[str]
    uncertainties: list[Annotated[str, Field(max_length=MAX_UNCERTAINTY)]]
    confidence: Literal["low", "medium", "high"]
    created_t: Annotated[float, Field(ge=0)]
    latency_ms: Annotated[float, Field(ge=0)]


def clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def normalize_draft(draft: RecommendationDraft | dict) -> RecommendationDraft:
    """截断超长字段并清洗，保证符合契约长度上限。"""
    d = draft if isinstance(draft, RecommendationDraft) else RecommendationDraft.model_validate(draft)
    return RecommendationDraft(
        summary=clip(d.summary, MAX_SUMMARY),
        explanation=clip(d.explanation, MAX_EXPLANATION),
        recommended_option_id=(d.recommended_option_id or "").strip() or None,
        evidence_ids=[e for e in dict.fromkeys(e.strip() for e in d.evidence_ids if e.strip())][:10],
        uncertainties=[clip(u, MAX_UNCERTAINTY) for u in d.uncertainties if u.strip()][:6],
        confidence=d.confidence,
    )


def validate_draft(
    draft: RecommendationDraft, known_ids: set[str], option_ids: set[str]
) -> list[str]:
    """ID 存在性校验，返回错误列表（空列表 = 通过）。"""
    errors: list[str] = []
    unknown = [e for e in draft.evidence_ids if e not in known_ids]
    if unknown:
        errors.append(f"evidence_ids 引用了上下文不存在的 ID: {unknown}")
    opt = draft.recommended_option_id
    if opt is not None and opt not in option_ids:
        errors.append(f"recommended_option_id {opt!r} 不在当前方案列表中")
    if len(draft.summary) > MAX_SUMMARY or len(draft.explanation) > MAX_EXPLANATION:
        errors.append("summary/explanation 超长（未正确截断）")
    if any(len(u) > MAX_UNCERTAINTY for u in draft.uncertainties):
        errors.append("uncertainties 存在超长条目")
    return errors
