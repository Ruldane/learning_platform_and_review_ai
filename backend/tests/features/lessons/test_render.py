"""Leçon en PDF (SPEC 3.5, 17.4, D89) : seuls nos fichiers figés s'exécutent, second essai sans
script si le rendu échoue, journaux sans contenu. Faux rendu : aucun Gotenberg."""

import logging
import re
from html import unescape

import pytest

from app.features.lessons.service.render import LESSON_READY, render_lesson_pdf
from app.templates.assets import asset
from tests.support.memory import FakeHtmlRenderer

# Page piégée : HTML brut, gestionnaires, liens et images, Mermaid avec directives.
TRAPPED = """# Leçon piégée

<script>fetch("http://backend:8000/api/v1/programs")</script>
<img src="http://169.254.169.254/latest" onerror="alert(1)">
<iframe src="file:///etc/passwd"></iframe>

## Objectifs

- Lire [la doc](https://docs.python.org/3/) et [ceci](javascript:alert(1)).
- ![pixel](https://evil.example/pixel.png)

## L'essentiel en 5 lignes

Une ligne <b onmouseover="x()">grasse</b>.

## Schémas

```mermaid
flowchart TD
A["Données"] --> B["Modèle"]
```

```mermaid
flowchart TD
A-->B
click A "javascript:alert(1)"
```

```mermaid
%%{init: {"securityLevel": "loose"}}%%
flowchart TD
A-->B
```

## Erreurs fréquentes

Oublier </main><script>alert(2)</script> de fermer.
"""
SECRET_TITLE = "Titre <script>alert(3)</script> secret"


async def test_lesson_html_has_no_content_script(fake_html_renderer: FakeHtmlRenderer) -> None:
    fake = fake_html_renderer
    pdf = await render_lesson_pdf(fake, title="T", markdown=TRAPPED, language="fr")
    assert pdf.startswith(b"%PDF")
    doc = fake.documents[0]
    assert re.findall(r"<script[^>]*>", doc.index_html) == [
        '<script src="mermaid.min.js">',
        '<script src="render.js">',
    ]
    assert set(doc.assets) == {"lesson.css", "mermaid.min.js", "render.js"}
    assert doc.footer_html is not None and "pageNumber" in doc.footer_html
    assert "totalPages" in doc.footer_html and "<script" not in doc.footer_html
    assert doc.wait_for_expression == LESSON_READY
    html = doc.index_html
    for trap in ("<img", "<iframe", "<b>", "<b "):
        assert trap not in html, trap
    # Un bloc HTML devient du texte échappé (D97), une balise en ligne est retirée (D89) :
    # aucune balise ni attribut ne porte un piège.
    tags = " ".join(re.findall(r"<[^>]*>", html))
    for trap in ("onerror", "onmouseover", "169.254", "evil.", "file:", "backend:8000"):
        assert trap not in tags, trap
    assert "&lt;img src=" in html and "onmouseover" not in html  # bloc échappé, en ligne retiré
    # Un lien refusé reste du texte inerte ; aucune adresse non http(s) dans un attribut.
    assert set(re.findall(r'href="([a-z]+):', html)) <= {"https"}
    assert html.count('<pre class="mermaid">') == 1  # click et %%{init} refusés
    assert html.count("diagram-unavailable") == 2
    assert doc.assets["mermaid.min.js"] == asset("mermaid.min.js")


async def test_lesson_page_has_toc_callouts_and_csp(fake_html_renderer: FakeHtmlRenderer) -> None:
    await render_lesson_pdf(fake_html_renderer, title=SECRET_TITLE, markdown=TRAPPED, language="fr")
    html = fake_html_renderer.documents[0].index_html
    assert '<html lang="fr">' in html
    assert html.count("<h1") == 1  # titre en couverture seulement, pas en double (D97)
    assert "<title>Titre &lt;script&gt;alert(3)&lt;/script&gt; secret</title>" in html
    assert '<nav class="toc">' in html and "Sommaire" in html
    assert re.search(r'<a href="#s2-l-essentiel-en-5-lignes">L(&#39;|\')essentiel', html)
    assert "callout-key" in html and "callout-warning" in html
    [csp] = re.findall(r'http-equiv="Content-Security-Policy" content="([^"]*)"', html)
    assert unescape(csp).startswith("default-src 'none'; script-src 'self';")
    assert "connect-src" not in html  # couvert par default-src 'none'


async def test_render_failure_retries_without_scripts(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    fake = FakeHtmlRenderer(failures=1)
    pdf = await render_lesson_pdf(fake, title=SECRET_TITLE, markdown=TRAPPED, language="fr")
    assert pdf.startswith(b"%PDF")
    first, second = fake.documents
    assert "<script" in first.index_html
    assert "<script" not in second.index_html
    assert set(second.assets) == {"lesson.css"} and second.wait_for_expression is None
    assert '<pre class="mermaid">' not in second.index_html
    assert second.index_html.count('<pre class="mermaid-source">') == 1
    assert "n1" in second.index_html  # la version réémise, jamais l'originale
    assert "secret" not in caplog.text and "Données" not in caplog.text


async def test_second_failure_is_raised() -> None:
    from app.providers.pdf.base import RenderFailed

    fake = FakeHtmlRenderer(failures=2)
    with pytest.raises(RenderFailed):
        await render_lesson_pdf(fake, title="T", markdown=TRAPPED, language="fr")
    assert len(fake.documents) == 2


async def test_lesson_without_diagram_has_no_script_at_all() -> None:
    fake = FakeHtmlRenderer()
    await render_lesson_pdf(fake, title="T", markdown="## A\n\ntexte", language="en")
    [doc] = fake.documents
    assert "<script" not in doc.index_html and set(doc.assets) == {"lesson.css"}
    assert doc.wait_for_expression is None and "script-src" not in doc.index_html
    assert '<html lang="en">' in doc.index_html and "Contents" in doc.index_html


@pytest.mark.parametrize("language", ['fr" onload="x', "", "../x", "ZZZ"])
async def test_language_is_sanitized(language: str) -> None:
    fake = FakeHtmlRenderer()
    await render_lesson_pdf(fake, title="T", markdown="texte", language=language)
    assert re.search(r'<html lang="[a-z]{2}">', fake.documents[0].index_html)
