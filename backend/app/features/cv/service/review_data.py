"""What CV reviews share (D130): readable errors, indicators stored as JSON and reread, order of
template sections, targeted text of a modification, offer title for the file name, views
rendered by the API. No CV text is logged here."""

import dataclasses
import re
from collections.abc import Sequence
from typing import Any, get_args

from app.agents.tools.cv_indicators import AtsCheck, Coverage, Indicators
from app.agents.tools.cv_schema import CvContent, CvLine, MasterProfileData, SectionKey
from app.agents.tools.template_schema import TemplateSpec
from app.core.errors import AppError
from app.db.models.career import CvModification, CvVersion
from app.features.cv.schemas_reviews import (
    AtsCheckOut,
    IndicatorsOut,
    ModificationOut,
    VersionOut,
)

CANONICAL_ORDER: list[SectionKey] = list(get_args(SectionKey))
VERSION_CATEGORY = "cv_versions"
# "(H/F)", "(F/H)", "(H/F/X)", "(m/w/d)": gender markers removed from the file name.
_GENDER = re.compile(r"\(\s*[a-z](\s*/\s*[a-z]){1,2}\s*\)", re.IGNORECASE)


def review_not_found() -> AppError:
    return AppError("review_not_found", "CV review not found.", 404)


def modification_not_found() -> AppError:
    return AppError("modification_not_found", "Modification not found.", 404)


def version_not_found() -> AppError:
    return AppError("version_not_found", "CV version not found.", 404)


def review_closed() -> AppError:
    return AppError(
        "review_closed",
        "Start a new review to generate another CV.",
        409,
    )


# --- Indicateurs ----------------------------------------------------------------------------


def coverage_json(value: Coverage) -> dict[str, Any]:
    return dataclasses.asdict(value)


def checks_json(checks: Sequence[AtsCheck]) -> dict[str, Any]:
    return {"checks": [dataclasses.asdict(check) for check in checks]}


def indicators_json(value: Indicators) -> dict[str, Any]:
    return {"coverage": coverage_json(value.coverage), **checks_json(value.checks)}


def indicators_of(data: dict[str, Any]) -> Indicators:
    coverage = Coverage(**data["coverage"])
    return Indicators(coverage, [AtsCheck(**check) for check in data.get("checks", [])])


def indicators_out(
    coverage: dict[str, Any] | None, checks: dict[str, Any] | None
) -> IndicatorsOut | None:
    if coverage is None:
        return None
    return IndicatorsOut(
        coverage_percent=int(coverage["percent"]),
        covered=int(coverage["covered"]),
        total=int(coverage["total"]),
        missing=[str(text) for text in coverage.get("missing", [])],
        checks=[AtsCheckOut.model_validate(c) for c in (checks or {}).get("checks", [])],
    )


def before_out(data: dict[str, Any] | None) -> IndicatorsOut | None:
    return None if data is None else indicators_out(data.get("coverage"), data)


# --- Contenu ---------------------------------------------------------------------------------


def template_order(spec: dict[str, Any] | None) -> list[SectionKey]:
    """The order of the template's sections (column 1 then 2, without the identity); the usual
    order without description."""
    if spec is None:
        return list(CANONICAL_ORDER)
    parsed = TemplateSpec.model_validate(spec)
    blocks = [block for column in parsed.columns for block in column.sections]
    return [block for block in dict.fromkeys(blocks) if block != "identity"]


def content_lines(content: CvContent) -> list[CvLine]:
    """All the lines of a CV: items of the sections, then lines of the entries."""
    lines: list[CvLine] = []
    for section in content.sections:
        lines += section.items
        for entry in section.entries:
            lines += entry.lines
    return lines


def target_text(base: CvContent, profile: MasterProfileData, target: str | None) -> str:
    """The original CV text that a modification targets (title, entry heading, line); empty if
    the target is not there (addition)."""
    if not target:
        return ""
    if profile.title is not None and profile.title.id == target and base.headline:
        return base.headline
    for section in base.sections:
        for entry in section.entries:
            if entry.fact_id == target:
                return entry.heading
    for line in content_lines(base):
        if line.fact_ids and line.fact_ids[0] == target:
            return line.text
    return ""


def posting_title(title: str | None) -> str | None:
    """The offer title for the file name, without the gender marker ("(H/F)")."""
    if not title:
        return None
    return " ".join(_GENDER.sub(" ", title).split()) or None


# --- Vues ------------------------------------------------------------------------------------


def modification_out(row: CvModification) -> ModificationOut:
    return ModificationOut.model_validate(
        {
            "id": row.id,
            "ref": row.ref,
            "section": row.section,
            "action": row.action,
            "type": row.type,
            "before": row.before,
            "after": row.after,
            "reason": row.reason,
            "status": row.status,
            "blocks": [str(block) for block in row.blocks],
            "fact_ids": [str(fact) for fact in row.fact_ids],
            "author": row.author,
        }
    )


def version_out(row: CvVersion) -> VersionOut:
    return VersionOut.model_validate(
        {
            "id": row.id,
            "review_id": row.review_id,
            "posting_id": row.posting_id,
            "number": row.number,
            "status": row.status,
            "page_count": row.page_count,
            "original_page_count": row.original_page_count,
            "allow_extra_pages": row.allow_extra_pages,
            "filename": row.filename,
            "decisions": {str(k): str(v) for k, v in row.decisions.items()},
            "indicators": indicators_out(row.coverage, row.ats),
            "created_at": row.created_at,
            "failure_reason": row.failure_reason,
        }
    )
