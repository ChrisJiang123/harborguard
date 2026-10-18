"""C3 models and two-layer validation. RecommendationDraft has the same generation schema for
cloud/local/template. Recommendation is the complete contract-v1 POST body. normalize_draft
truncates allowed text and deduplicates. validate_draft checks actual context IDs, supplementing B's
422 checks. Implementation forbids alert-level changes and /api/decision.
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
    """Require all six model fields explicitly, with no defaults."""

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
    """Apply only contract-allowed text truncation; never remove, replace or filter model IDs."""
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
    """Check ID existence and return errors; an empty list means valid."""
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
    """Raw model output is not a valid RecommendationDraft with actual context IDs."""


def parse_model_draft(raw: str, known_ids: set[str], option_ids: set[str]) -> RecommendationDraft:
    """Strictly parse a single JSON object, truncate valid overlong text and validate all IDs. Do not
    extract Markdown fences or delete invalid fields/IDs; the model must correct them on retry.
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
