"""Faux port des gabarits de CV (`FakeCvTemplateStore`) en mémoire, idempotent comme le contrat
(`prepare` par gabarit, `render_pass` par passe, `finish` par gabarit), et les réponses du
Maquettiste pour le CV fictif de `scripts/sample_cv.py` (« Camille Exemple »). Aucun réseau ni
LLM, aucune image réelle (des octets marqueurs tiennent lieu de PNG).

`render_calls` compte les **appels** au port par passe (preflight G34), `rendered` les passes
réellement rendues ; `calls` garde le nom de chaque appel, dans l'ordre."""

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.cv_schema import CvContent
from app.agents.tools.cv_template_port import (
    OriginalView,
    PassResult,
    TemplateOutcome,
    keeps_pass,
)
from app.agents.tools.template_schema import TemplateSpec
from app.agents.tools.template_similarity import Similarity, ZoneDiff
from app.core.errors import AppError
from app.providers.fonts.catalog import FontChoice
from scripts.sample_cv import CV_FACTS
from tests.support.cv_template import content as cv_content
from tests.support.cv_template import spec as cv_spec
from tests.support.profile import CV_TEXT

F = CV_FACTS
ORIGINAL_PNG = b"\x89PNG-original-page-1"
FONTS = ["Lato", "Carlito", "Liberation Sans"]
BLOCKS = "\n".join(
    [
        f"40,40,200,24 | Helvetica-Bold | 22 | #21549a | oui | {F['name']}",
        f"40,70,200,14 | Helvetica | 11 | #222222 | non | {F['title']}",
    ]
)


def render_png(pass_no: int) -> bytes:
    return f"\x89PNG-rendu-passe-{pass_no}".encode()


def sample_dict(**over: Any) -> dict[str, Any]:
    """Le contenu que le Maquettiste recopie du CV fictif : chaque texte figure dans `CV_TEXT`
    (le résumé y est coupé en deux lignes, les puces y portent « • »)."""
    data: dict[str, Any] = {
        "name": F["name"],
        "headline": F["title"],
        "contact": [F["email"], F["phone"]],
        "sections": [
            {
                "key": "summary",
                "title": "Profil",
                "items": [
                    {
                        "text": f"{F['title']}, cinq ans d'expérience en données et en agents "
                        "conversationnels."
                    }
                ],
            },
            {
                "key": "experience",
                "title": "Expériences",
                "entries": [
                    {
                        "heading": f"{F['role_1']} — {F['company_1']}",
                        "dates": F["period_1"],
                        "lines": [
                            {"text": "Conçu un assistant interne avec LangGraph pour le support"},
                            {"text": f"Réduit de {F['metric_1']} le temps de traitement"},
                        ],
                    }
                ],
            },
            {"key": "languages", "title": "Langues", "items": [{"text": F["language"]}]},
        ],
    }
    data.update(over)
    return data


def sample_reply(**over: Any) -> str:
    return json.dumps(sample_dict(**over), ensure_ascii=False)


def spec_reply(**over: Any) -> str:
    """Une description valable (deux colonnes, Lato) ; `over` remplace des champs."""
    return json.dumps(cv_spec().model_dump(mode="json") | over, ensure_ascii=False)


def similarity(score: int) -> Similarity:
    return Similarity(
        score=score,
        ink=score / 100,
        text=score / 100,
        color=0.9,
        pages_original=1,
        pages_render=1,
        zones=[ZoneDiff(zone="haut", original=0.30, render=0.20)],
    )


def original_view(template_id: str, *, selectable: bool = True) -> OriginalView:
    return OriginalView(
        template_id=template_id,
        page_count=1,
        page_size=(595.0, 842.0),
        selectable=selectable,
        pages_png=[ORIGINAL_PNG],
        blocks_summary=BLOCKS,
        fonts=[FontChoice(original="Helvetica", family="Liberation Sans", free=False)],
        available_fonts=list(FONTS),
        original_text=CV_TEXT if selectable else "",
    )


@dataclass
class FakeCvTemplateStore:
    scores: list[int] = field(default_factory=lambda: [90])  # score de la passe n : scores[n-1]
    selectable: bool = True
    profile_content: CvContent | None = None
    calls: list[str] = field(default_factory=list)
    render_calls: Counter[int] = field(default_factory=Counter)
    rendered: list[int] = field(default_factory=list)
    passes: dict[int, tuple[TemplateSpec, CvContent, PassResult]] = field(default_factory=dict)
    finished: dict[str, tuple[TemplateOutcome, str | None]] = field(default_factory=dict)
    prepared: list[str] = field(default_factory=list)
    kept: int | None = None  # passe gardée (`keeps_pass`) ; rangée avec `finish`
    finished_pass: dict[str, int | None] = field(default_factory=dict)  # passe gardée au `finish`

    async def prepare(self, user_id: str, template_id: str) -> OriginalView:
        self.calls.append("prepare")
        if template_id not in self.prepared:
            self.prepared.append(template_id)
        return original_view(template_id, selectable=self.selectable)

    async def sample_fallback(self, user_id: str) -> CvContent | None:
        self.calls.append("sample_fallback")
        return self.profile_content

    async def render_pass(
        self,
        user_id: str,
        template_id: str,
        pass_no: int,
        spec: TemplateSpec,
        content: CvContent,
        adjusted: bool = False,
    ) -> PassResult:
        self.calls.append("render_pass")
        self.render_calls[pass_no] += 1
        if pass_no not in self.passes:
            score = self.scores[min(pass_no, len(self.scores)) - 1]
            result = PassResult(pass_no, score, similarity(score), [render_png(pass_no)])
            self.passes[pass_no] = (spec, content, result)
            self.rendered.append(pass_no)
            kept = None if self.kept is None else self.passes[self.kept][2].score
            if keeps_pass(adjusted, score, kept):
                self.kept = pass_no
        return self.passes[pass_no][2]

    async def read_pass(self, user_id: str, template_id: str, pass_no: int) -> PassResult:
        self.calls.append("read_pass")
        if pass_no not in self.passes:
            raise AppError("template_pass_not_found", "Passe introuvable.", 404)
        return self.passes[pass_no][2]

    async def finish(
        self, user_id: str, template_id: str, status: TemplateOutcome, reason: str | None
    ) -> None:
        self.calls.append("finish")
        self.finished.setdefault(template_id, (status, reason))
        self.finished_pass.setdefault(template_id, self.kept)

    def spec_of(self, pass_no: int) -> TemplateSpec:
        return self.passes[pass_no][0]


def profile_sample() -> CvContent:
    """Le contenu du profil validé (CV scanné)."""
    return cv_content()
