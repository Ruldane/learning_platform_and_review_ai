"""Les phrases du radar du marché (D159) : toujours les nombres réels (lues, bloquées, pas des
offres, analysées) et jamais un échantillon que le relevé n'a pas (SPEC 1, 18.3). Aucune entrée-
sortie ici."""

from app.agents.tools.radar_port import RadarSummary

UNAVAILABLE_TEXT = "La recherche web ne répond pas : relevé impossible pour l'instant."
NO_MODEL_TEXT = "Aucun modèle n'est utilisable (clé absente ?) : relevé impossible pour l'instant."
NO_ANALYSIS_TEXT = (
    "Les offres lues n'ont pas pu être analysées (le modèle ne répond pas) : relevé non terminé."
)


def _count(number: int, one: str, many: str) -> str:
    """« 0 offre lue », « 1 offre lue », « 2 offres lues » (le français accorde dès 2)."""
    return f"{number} {one if number < 2 else many}"


def counting_text(readable: int, blocked: int) -> str:
    """Après un passage de lecture : « 24 pages lues : 19 offres, 5 bloquées. »"""
    pages = _count(readable + blocked, "page lue", "pages lues")
    offers = _count(readable, "offre", "offres")
    return f"{pages} : {offers}, {_count(blocked, 'bloquée', 'bloquées')}."


def summary_text(report: RadarSummary) -> str:
    """« 47 offres lues, 6 bloquées, 41 analysées. » Les pages lisibles qui ne sont pas des offres
    sont comptées à part (« 3 pages qui n'étaient pas des offres »), jamais dans les offres."""
    offers = report.read_ok - report.not_postings
    parts = [
        _count(offers, "offre lue", "offres lues"),
        _count(report.blocked, "bloquée", "bloquées"),
    ]
    if report.not_postings:
        parts.append(
            _count(
                report.not_postings, "page n'était pas une offre", "pages n'étaient pas des offres"
            )
        )
    parts.append(_count(report.analyzed, "analysée", "analysées"))
    return ", ".join(parts) + "."


def sample_text(report: RadarSummary) -> str | None:
    """La mention d'un échantillon réduit (moins de 30 offres lisibles), sinon `None`."""
    if not report.low_sample:
        return None
    offers = report.read_ok - report.not_postings
    if offers < 1:
        return "Aucune offre lisible : pas de classement cette fois."
    return f"Seulement {_count(offers, 'offre lisible', 'offres lisibles')} : classement indicatif."
