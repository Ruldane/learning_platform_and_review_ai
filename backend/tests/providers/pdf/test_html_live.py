"""Leçon rendue par un vrai Gotenberg (D89) : marqué `live`, désélectionné par défaut.

Gotenberg n'a aucun port publié : publier un Gotenberg jetable lancé avec les options de
`docker-compose.yml` (par exemple sur `127.0.0.1:3999`) et passer son adresse dans
`GOTENBERG_URL` ; `LESSON_PDF_OUT` garde le PDF pour le regarder."""

import os
from pathlib import Path

import httpx
import pytest

from app.features.lessons.service.markdown import markdown_to_html
from app.features.lessons.service.render import lesson_document, render_lesson_pdf
from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S
from app.providers.pdf.extract import PdfPlumberExtractor
from app.providers.pdf.html import GotenbergHtmlRenderer

pytestmark = pytest.mark.live

LESSON = """## Objectifs

Comprendre le pipeline.

## L'essentiel en 5 lignes

Une ligne <img src="x" onerror="document.title='pirate'"> sûre.

## Schémas

```mermaid
flowchart LR
A["Données"] --> B["Modèle"]
```

## Erreurs fréquentes

Oublier la validation.
"""

# Un tableau de chaque type (formes, sous-graphes, libellés d'arête, `<br>`, entités).
BOARDS = {
    "Carte": (
        'flowchart TD\nIA["Intelligence artificielle"] --> ML["Apprentissage"]\n'
        'ML -->|"s\'appuie sur"| STATS["Statistiques"]\nsubgraph Produit\n  direction LR\n'
        '  API["API de LLM"] --- RAG["Recherche augmentée"]\nend\nML --> API'
    ),
    "Prérequis": 'graph LR\nPY["Python"] --> HTTP["Appels HTTP"]\nHTTP -.-> PROD{Mise en prod}',
    "Frise": 'flowchart LR\nS1["Semaine 1<br>bases"] --> S2["A < B & C"]\nS2 ==> P(("Fin"))',
    "Comparaison": (
        'flowchart TD\nsubgraph P1["Parcours pratique"]\n  A1["8 semaines"]\nend\n'
        'subgraph P2["Parcours socle"]\n  A2["12 semaines"]\nend\nP1 -. compare .- P2'
    ),
}


@pytest.fixture
def gotenberg_url() -> str:
    url = os.environ.get("GOTENBERG_URL")
    if not url:
        pytest.skip("GOTENBERG_URL n'est pas définie")
    return url


async def test_gotenberg_renders_lesson_with_svg_diagram(gotenberg_url: str) -> None:
    async with httpx.AsyncClient(trust_env=False, timeout=HTML_RENDER_TIMEOUT_S) as http:
        renderer = GotenbergHtmlRenderer(http, gotenberg_url)
        pdf = await render_lesson_pdf(renderer, title="Pipeline", markdown=LESSON, language="fr")
    assert pdf.startswith(b"%PDF")
    keep = os.environ.get("LESSON_PDF_OUT")
    if keep:
        Path(keep).write_bytes(pdf)
    text = " ".join((await PdfPlumberExtractor().extract_text(pdf)).split())
    assert "Données" in text and "Modèle" in text
    # Rendu en SVG : le code réémis (`n1["…"]`, `flowchart`) n'apparaît pas.
    assert "flowchart" not in text and "n1" not in text
    assert "Sommaire" in text and "pirate" not in text
    assert "Pipeline 1 / 1" in text  # pied de page : titre et numéros


async def test_gotenberg_renders_lesson_without_script(gotenberg_url: str) -> None:
    """Second essai d'une leçon (aucun script) : les schémas sont du code, le PDF sort."""
    content = markdown_to_html(LESSON)
    document = lesson_document(
        title="Pipeline", body=content.html, toc=content.toc, language="fr", scripts=False
    )
    async with httpx.AsyncClient(trust_env=False, timeout=HTML_RENDER_TIMEOUT_S) as http:
        pdf = await GotenbergHtmlRenderer(http, gotenberg_url).html_to_pdf(document)
    text = " ".join((await PdfPlumberExtractor().extract_text(pdf)).split())
    assert "flowchart LR" in text and "Données" in text


async def test_gotenberg_renders_every_board_kind_as_svg(gotenberg_url: str) -> None:
    """Les quatre types de tableau du Scribe, réémis (`n1`…, entités `#lt;`), passent dans
    Mermaid : aucun ne retombe en code."""
    blocks = "\n\n".join(f"## {kind}\n\n```mermaid\n{code}\n```" for kind, code in BOARDS.items())
    async with httpx.AsyncClient(trust_env=False, timeout=HTML_RENDER_TIMEOUT_S) as http:
        renderer = GotenbergHtmlRenderer(http, gotenberg_url)
        pdf = await render_lesson_pdf(renderer, title="Tableaux", markdown=blocks, language="fr")
    text = " ".join((await PdfPlumberExtractor().extract_text(pdf)).split())
    assert "flowchart" not in text and "#lt;" not in text and "n1" not in text
    assert "Statistiques" in text and "Parcours socle" in text
