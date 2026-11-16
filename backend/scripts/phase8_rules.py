"""Règles du contrôle de la phase 8 (`check_phase8`), en fonctions pures : chacune lit une
réponse de l'API déjà reçue (relevé du radar, brief du jour) ou les journaux du back, et lève
`CheckFailed` quand une règle n'est pas tenue. Les messages ne portent que des étapes, des
nombres, des rangs et des noms de rubriques : jamais un poste, une zone, un lien, une entreprise
ni une phrase du conseil."""

import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from scripts.phase4_rules import CheckFailed
from scripts.phase7_rules import check_logs

ROLE = "Développeur Python"  # le poste et la zone fictifs, génériques, du relevé de contrôle
ZONE = "Lyon"
MAX_READS = 60  # lectures d'un relevé (lisibles + bloquées), plafond du parcours
MIN_RUN = 30  # sous ce nombre d'offres lisibles, l'échantillon est dit réduit
HIGH_MATCH = 70  # le score au moins duquel une offre entre au brief
RUBRICS = ("block", "reviews", "reminders", "offers", "week", "resource", "advice")
ADVICE_SENTENCES = 2
MIN_EXTRA = 4  # un texte plus court qu'ici n'est pas cherché dans les journaux (trop banal)
PLANNED_DELAY_MIN = 3
_DIGITS = re.compile(r"\d+")

# Ce que les journaux ne contiennent jamais (17.2) : le poste et la zone envoyés au radar ; les
# textes propres à ce passage (lien et intitulé de la ressource, phrases du conseil, liens,
# intitulés et entreprises des offres) s'ajoutent par `log_extras`.
PHASE8_FORBIDDEN = (ROLE, ZONE)


def target_moment(now: datetime) -> datetime:
    """L'heure réglée du brief : trois minutes plus tard, à la minute (heure locale de `now`)."""
    return (now + timedelta(minutes=PLANNED_DELAY_MIN)).replace(second=0, microsecond=0)


def check_same_day(step: str, now: datetime, target: datetime) -> None:
    if target.date() != now.date():
        raise CheckFailed(step, "Trop près de minuit : l'heure réglée tomberait demain. Réessaie.")


def figures_of(text: str) -> list[str]:
    return _DIGITS.findall(text)


def salary_missing(salary: str, page: str) -> bool:
    """Vrai si le salaire rapporté n'est pas dans la page relue : un salaire sans chiffre, ou un
    de ses nombres (entier de chiffres : 45 n'est pas 450) qui n'y figure pas."""
    figures = figures_of(salary)
    present = set(figures_of(page))
    return not figures or any(figure not in present for figure in figures)


def _fail(step: str, message: str) -> CheckFailed:
    return CheckFailed(step, message)


def check_report(step: str, run: dict[str, Any]) -> dict[str, int]:
    """Les règles d'un relevé fini, lues par l'API ; rend ses nombres (pour l'affichage)."""
    read, blocked = int(run["read_count"]), int(run["blocked_count"])
    analyzed, not_postings = int(run["analyzed"]), int(run["not_postings"])
    if read + blocked > MAX_READS:
        raise _fail(step, f"{read} lue(s) + {blocked} bloquée(s) : {MAX_READS} lectures au plus.")
    if analyzed + not_postings > read:
        raise _fail(step, f"{analyzed} analysée(s) + {not_postings} sans offre > {read} lue(s).")
    if len(run["offers"]) != analyzed:
        raise _fail(step, f"{len(run['offers'])} offre(s) rendue(s) pour {analyzed} analysée(s).")
    if sum(int(d["count"]) for d in run["blocked_domains"]) != blocked:
        raise _fail(step, "Les sites bloqués ne totalisent pas le nombre de pages bloquées.")
    if analyzed > 0 and not run["ranking"]:
        raise _fail(step, f"Classement vide pour {analyzed} offre(s) analysée(s).")
    if bool(run["low_sample"]) != (read - not_postings < MIN_RUN):
        raise _fail(
            step, f"`low_sample` incohérent avec {read - not_postings} offre(s) lisible(s)."
        )
    scores = [int(offer["score"]) for offer in run["offers"]]
    if scores != sorted(scores, reverse=True) or any(not 0 <= s <= 100 for s in scores):
        raise _fail(step, "Scores des offres hors de 0 à 100 ou pas du meilleur au moindre.")
    return {
        "read": read,
        "blocked": blocked,
        "analyzed": analyzed,
        "not_postings": not_postings,
        "not_analyzed": int(run["not_analyzed"]),
        "high": sum(1 for score in scores if score >= HIGH_MATCH),
    }


def check_rubrics(step: str, brief: dict[str, Any]) -> None:
    """Les sept rubriques sont là (le bloc, la semaine, la ressource et le conseil peuvent être
    vides) ; les trois autres sont toujours rangées, avec leurs plafonds."""
    missing = [name for name in RUBRICS if name not in brief]
    if missing:
        raise _fail(step, f"Rubrique(s) absente(s) du brief : {', '.join(missing)}.")
    reviews, reminders, offers = brief["reviews"], brief["reminders"], brief["offers"]
    if not isinstance(reviews, dict) or not isinstance(reminders, dict):
        raise _fail(step, "Rubriques `reviews` et `reminders` attendues rangées.")
    if not isinstance(offers, dict) or len(offers["items"]) > 5 or len(reminders["items"]) > 5:
        raise _fail(step, "Rubrique `offers` ou `reminders` : 5 éléments au plus.")
    if any(int(item["score"]) < HIGH_MATCH for item in offers["items"]):
        raise _fail(step, f"Une offre du brief a un score sous {HIGH_MATCH}.")
    if bool(offers["items"]) != (offers["run_id"] is not None):
        raise _fail(step, "`offers.run_id` incohérent avec les offres montrées.")


def rubric_numbers(brief: dict[str, Any]) -> set[str]:
    """Les nombres que les rubriques disent : leurs entiers, et le nombre d'éléments de leurs listes
    (les offres montrées, les relances montrées)."""
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, int):
            found.add(str(abs(value)))
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            found.add(str(len(value)))
            for child in value:
                walk(child)

    for name in ("block", "reviews", "reminders", "offers", "week"):
        walk(brief.get(name))
    return found


def check_advice(step: str, brief: dict[str, Any]) -> int:
    """Le conseil est prêt : deux phrases, chaque nombre cité figure dans les rubriques. Rend le
    nombre de nombres cités ; un état définitif autre que `ready` est dit avec son nom."""
    status = brief["advice_status"]
    if status != "ready":
        raise _fail(step, f"Conseil « {status} » : définitif pour la journée, jamais relancé.")
    sentences = brief["advice"]
    if not isinstance(sentences, list) or len(sentences) != ADVICE_SENTENCES:
        count = len(sentences) if isinstance(sentences, list) else 0
        raise _fail(step, f"{count} phrase(s) de conseil, {ADVICE_SENTENCES} attendues.")
    if any(not str(sentence).strip() for sentence in sentences):
        raise _fail(step, "Une phrase du conseil est vide.")
    cited = [figure for sentence in sentences for figure in figures_of(str(sentence))]
    unknown = sorted(set(cited) - rubric_numbers(brief), key=int)
    if unknown:
        raise _fail(step, f"{len(unknown)} nombre(s) du conseil absent(s) des rubriques.")
    return len(cited)


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def check_resource(step: str, resource: dict[str, Any] | None) -> str:
    """Rien (`None`, dit) ou une ressource complète, au lien http(s) de son site. Rend son site."""
    if resource is None:
        return ""
    if any(not str(resource.get(key) or "").strip() for key in ("title", "url", "domain", "why")):
        raise _fail(step, "Ressource du jour : titre, lien, site ou raison manquant.")
    host, domain = _host(str(resource["url"])), str(resource["domain"]).lower().removeprefix("www.")
    if not str(resource["url"]).startswith(("http://", "https://")) or domain not in host:
        raise _fail(step, "Ressource du jour : lien non http(s) ou site différent de son lien.")
    return domain


def log_extras(radar: dict[str, Any] | None, brief: dict[str, Any] | None) -> list[str]:
    """Les textes de ce passage que les journaux ne portent jamais : le poste et la zone du relevé,
    les liens, intitulés et entreprises de ses offres et de celles du brief, la ressource et les
    phrases du conseil."""
    texts: list[Any] = []
    if radar:
        texts += [radar.get("role"), radar.get("zone")]
        for offer in radar.get("offers", []):
            texts += [offer.get("url"), offer.get("title"), offer.get("company")]
    if brief:
        resource = brief.get("resource") or {}
        texts += [resource.get("url"), resource.get("title"), *(brief.get("advice") or [])]
        for offer in (brief.get("offers") or {}).get("items", []):
            texts += [offer.get("url"), offer.get("title"), offer.get("company")]
    found = {str(text).strip() for text in texts if text}
    return sorted(text for text in found if len(text) >= MIN_EXTRA)


def check_logs_8(step: str, logs: str, extra: list[str]) -> int:
    """Aucune donnée dans les journaux (phases 6 et 7 comprises) ; rend le nombre de lignes lues."""
    return check_logs(step, logs, (*PHASE8_FORBIDDEN, *extra))
