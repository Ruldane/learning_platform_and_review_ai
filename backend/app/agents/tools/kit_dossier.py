"""Contrôle et rendu du dossier de l'entreprise (SPEC 6.4, F16, D142). Du code : le rôle du
Vérificateur est tenu ici, « aucune affirmation sans source lue » :

- une citation `[n]` dont la page n'a pas été lue est retirée du texte ;
- un texte (activité, produit, culture, processus d'entretien) qui ne cite plus aucune page lue
  est vidé : le rendu dit « Non trouvé dans les sources lues. » ;
- une technologie, un point de vigilance ou une actualité sans citation valide est retiré ;
- une actualité sans date, future ou de plus de 6 mois est retirée ; de même celle dont toutes
  les pages citées portent une date connue de plus de 6 mois (la date du modèle ne suffit pas) ;
- les questions à poser sont des questions, pas des affirmations : leurs citations invalides
  sont retirées, une question réduite à rien n'est pas rendue ;
- la taille de l'entreprise n'est pas sourcée : rendue comme une estimation, omise si inconnue.

Aucune journalisation ici : le dossier n'est jamais écrit dans un journal (17.2)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.agents.tools.kit_schema import CompanyDossier, NewsItem, SourceRef

NEWS_MAX_AGE = timedelta(days=183)
UNSOURCED = "Non trouvé dans les sources lues."
SIZES = {"startup": "startup", "pme": "PME", "grand_groupe": "grand groupe", "inconnu": "inconnue"}
_CITATION = re.compile(r"\s*\[(\d+(?:\s*[,;]\s*\d+)*)\]")
_NUMBER = re.compile(r"\d+")


def _cleaned(text: str, valid: set[int]) -> tuple[str, int]:
    """`text` sans les citations de pages non lues, et le nombre de citations valides restantes."""
    kept = 0

    def keep(match: re.Match[str]) -> str:
        nonlocal kept
        numbers = [int(n) for n in _NUMBER.findall(match.group(1))]
        good = [n for n in numbers if n in valid]
        kept += len(good)
        return f" [{', '.join(str(n) for n in good)}]" if good else ""

    return _CITATION.sub(keep, text).strip(), kept


def _sourced(text: str, valid: set[int]) -> str:
    """Le texte nettoyé, ou vide s'il ne cite aucune page lue."""
    clean, kept = _cleaned(text, valid)
    return clean if kept else ""


@dataclass(frozen=True)
class Checked:
    """Le dossier vérifié ; `emptied` : les textes vidés, `dropped` : les éléments retirés."""

    dossier: CompanyDossier
    emptied: int
    dropped: int


def _fresh(item: NewsItem, today: date) -> bool:
    return item.date is not None and today - NEWS_MAX_AGE <= item.date <= today


def _from_old_pages(text: str, page_dates: Sequence[date | None], today: date) -> bool:
    """Toutes les pages citées ont une date connue de plus de 6 mois (une page sans date, ou une
    page récente parmi elles, laisse le doute à l'actualité)."""
    cited = [int(n) for match in _CITATION.findall(text) for n in _NUMBER.findall(match)]
    dates = [page_dates[n - 1] if n <= len(page_dates) else None for n in cited]
    return bool(dates) and all(d is not None and d < today - NEWS_MAX_AGE for d in dates)


def check_dossier(
    dossier: CompanyDossier, pages: int, today: date, *, page_dates: Sequence[date | None] = ()
) -> Checked:
    """Le dossier d'un modèle, vérifié contre les `pages` lues (rangs 1 à `pages`), le jour et la
    date connue de chaque page (`page_dates`, dans l'ordre des rangs)."""
    valid = set(range(1, pages + 1))
    texts = {
        name: _sourced(getattr(dossier, name), valid)
        for name in ("activity", "product", "culture", "interview_process")
    }
    stack = [s for s in (_sourced(item, valid) for item in dossier.stack) if s]
    points = [s for s in (_sourced(item, valid) for item in dossier.watch_points) if s]
    news = []
    for item in dossier.news:
        cited = _sourced(item.text, valid)
        if cited and _fresh(item, today) and not _from_old_pages(cited, page_dates, today):
            news.append(NewsItem(text=cited, date=item.date))
    questions = [_cleaned(question, valid)[0] for question in dossier.questions]
    checked = dossier.model_copy(
        update={
            **texts,
            "stack": stack,
            "watch_points": points,
            "news": news,
            "questions": questions,
        }
    )
    dropped = (
        len(dossier.stack) - len(stack)
        + len(dossier.watch_points) - len(points)
        + len(dossier.news) - len(news)
    )  # fmt: skip
    return Checked(checked, sum(1 for text in texts.values() if not text), dropped)


def has_content(dossier: CompanyDossier) -> bool:
    """Au moins un texte sourcé : sinon le dossier n'est pas produit."""
    texts = (dossier.activity, dossier.product, dossier.culture, dossier.interview_process)
    return any(texts) or bool(dossier.stack or dossier.news or dossier.watch_points)


def _section(title: str, body: str) -> str:
    return f"## {title}\n{body or UNSOURCED}"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_dossier(company: str, dossier: CompanyDossier, sources: list[SourceRef]) -> str:
    """Le dossier en Markdown, avec la liste des pages lues."""
    news = [f"{item.date.isoformat() if item.date else ''} : {item.text}" for item in dossier.news]
    asked = [text for text in dossier.questions if text.strip()]
    questions = "\n".join(f"{rank}. {text}" for rank, text in enumerate(asked, 1))
    known = dossier.size != "inconnu"
    listed = [
        f"[{rank}] {source.title or source.url} — {source.url}"
        for rank, source in enumerate(sources, 1)
    ]
    parts = [
        f"# Dossier : {company}",
        _section("Activité", dossier.activity),
        _section("Produit", dossier.product),
        _section("Technologies", _bullets(dossier.stack)),
        _section("Actualité (moins de 6 mois)", _bullets(news)),
        _section("Culture", dossier.culture),
        _section("Processus d'entretien", dossier.interview_process),
        _section("Cinq questions à poser", questions),
        _section("Points de vigilance", _bullets(dossier.watch_points)),
        *([f"Taille estimée : {SIZES[dossier.size]} (estimation non sourcée)"] if known else []),
        _section("Sources", "\n".join(listed)),
    ]
    return "\n\n".join(parts)
