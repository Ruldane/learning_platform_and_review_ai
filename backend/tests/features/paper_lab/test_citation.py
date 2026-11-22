import pytest

from app.agents.tools.paper_lab_port import ArticleSource, ExperimentDraft, PaperDraft, cited_course
from app.core.errors import AppError
from tests.e2e.paper_lab import CODE, COURSE, MATERIAL, QUOTE, RESULT, TITLE, URL


def test_article_excerpt_is_verified_before_entering_the_course() -> None:
    source = ArticleSource(URL, TITLE, MATERIAL.replace("obtient une", "obtient\nune"))
    draft = PaperDraft(
        title=TITLE,
        course=COURSE,
        source_quote=QUOTE,
        experiment=ExperimentDraft(
            method="Calculer la pente des points alignés.", code=CODE, expected=RESULT
        ),
    )
    assert cited_course(source, draft).endswith(f"> {QUOTE}")
    invented = draft.model_copy(update={"source_quote": "L’article donne une pente de 10,0."})
    with pytest.raises(AppError, match="L’extrait cité"):
        cited_course(source, invented)
