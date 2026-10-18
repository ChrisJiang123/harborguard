"""Agent 模型与双重校验（C3）。

- RecommendationDraft：生成侧草案（云端/本地/模板三处同构）。
- Recommendation：契约 v1 的完整建议（POST /api/recommendations 请求体）。
- normalize_draft：超长字段截断、去重。
- validate_draft：**上下文真实 ID** 校验（evidence_ids / recommended_option_id），
  与后端 422 校验形成双保险；禁改警报等级、禁调 /api/decision 由实现保证。
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from .language import CJK, clip_field, language, text_errors

MAX_SUMMARY = 60
MAX_EXPLANATION = 300
MAX_UNCERTAINTY = 40


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


Nonblank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Trimmed = Annotated[str, StringConstraints(strip_whitespace=True)]


class RecommendationDraft(StrictModel):
    """模型必须显式给出全部六个字段；不提供任何默认值。"""

    summary: Nonblank
    explanation: Nonblank
    recommended_option_id: Nonblank | None
    evidence_ids: list[Nonblank]
    uncertainties: list[Trimmed]
    confidence: Literal["low", "medium", "high"]


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
    """只做契约允许的文本截断；不删除、替换或过滤任何模型输出 ID。"""
    d = draft if isinstance(draft, RecommendationDraft) else RecommendationDraft.model_validate(draft)
    return RecommendationDraft(
        summary=clip_field(d.summary, "summary"),
        explanation=clip_field(d.explanation, "explanation"),
        recommended_option_id=d.recommended_option_id,
        evidence_ids=list(d.evidence_ids),
        uncertainties=[clip_field(u, "uncertainties") for u in d.uncertainties],
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
    errors.extend(text_errors(draft))
    return errors


class DraftOutputError(ValueError):
    """模型原始输出不是合法、真实 ID 的 RecommendationDraft。"""


def parse_model_draft(raw: str, known_ids: set[str], option_ids: set[str]) -> RecommendationDraft:
    """严格解析单个 JSON 对象，再截断合法长文本并校验全部 ID。

    不尝试提取 Markdown 代码块或删除坏字段/坏 ID；模型必须自行在重试时修正。
    """
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise DraftOutputError(f"输出不是 JSON 对象: {exc.msg if hasattr(exc, 'msg') else exc}") from exc
    if not isinstance(payload, dict):
        raise DraftOutputError("JSON 顶层必须是对象")
    try:
        original = RecommendationDraft.model_validate(payload)
        if language() == "en" and any(CJK.search(t) for t in
                                       [original.summary, original.explanation, *original.uncertainties]):
            raise DraftOutputError("English output required; CJK output rejected before truncation")
        draft = normalize_draft(original)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in item['loc'])}: {item['msg']}" for item in exc.errors()[:8]
        )
        raise DraftOutputError(f"结构校验失败: {details}") from exc
    errors = validate_draft(draft, known_ids, option_ids)
    if errors:
        raise DraftOutputError("; ".join(errors))
    return draft
