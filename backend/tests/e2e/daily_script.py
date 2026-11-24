"""Scénario du parcours de bout en bout n° 4 (« le brief à l'ouverture et un relevé du radar »,
SPEC 18.2, P18) : les réponses scriptées du brief et du radar, et le web factice qu'ils lisent.

- Brief (`daily_brief`) : l'Éclaireur choisit le résultat n° 2 de la recherche du sujet du jour
  (`TOPIC_QUERY`, « {poste} actualités » : le poste est celui des réglages du radar, que le parcours
  pose avant d'ouvrir l'accueil) ; le code lit la page. Le Modérateur écrit deux phrases sans aucun
  nombre : le code refuse un nombre que les faits du jour ne disent pas, et ceux du jour dépendent
  des autres parcours (programme, révisions) ;
- Radar (`market_radar`) : les requêtes sont celles du code (`radar_searches`), la recherche en
  rend onze liens (huit offres lisibles, trois pages que le web factice ne sait pas lire : elles
  sont comptées « bloquées »). L'Analyste lit les offres par lots de cinq ; **le repère d'une page
  (`p1`…) dépend de l'ordre où les lectures simultanées finissent**, il ne dit donc rien de
  l'offre : la réponse la reconnaît à sa ligne de référence (`REFERENCE`) dans le texte du lot.

Chaque réponse n'est servie que pour son appel (`dispatch` : le marqueur de la demande dans le
prompt), les autres scénarios gardent les leurs (`merge_scripts`, `OutOfOrder`)."""

import json
import re
from collections.abc import Sequence
from typing import Any, NamedTuple

from langchain_core.messages import BaseMessage

from app.agents.nodes.analyst_radar import RADAR_REQUEST
from app.agents.tools.radar_schema import radar_searches
from app.providers.search.base import SearchResult
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebDocument
from tests.e2e.cv_script import dispatch
from tests.e2e.lesson_script import prompt_of
from tests.e2e.scripted_models import Reply
from tests.support.memory import FakeWebReader

ROLE = "Ingénieure données"
ZONE = "Lyon"
LANGUAGES = ("fr", "en")  # `search_languages` par défaut : les requêtes du radar en dépendent
LONG = 12  # réponses prévues par agent : bien plus que les appels du parcours

# --- Brief -----------------------------------------------------------------------------------

PICK_REQUEST = "Choose today's resource."  # The Scout's request.
ADVICE_REQUEST = "Write today's advice."  # The Moderator's request.
TOPIC_QUERY = f"{ROLE} actualités"
PICKED = 2  # le rang du résultat choisi (à partir de 1)
WHY = "Un état des lieux récent du métier, utile pour ton poste visé."
SENTENCES = [
    "Commence par ton bloc d'étude du jour, puis garde un moment pour les révisions.",
    "Les relances et les nouvelles offres peuvent attendre la fin de ta session.",
]


class Resource(NamedTuple):
    title: str
    url: str
    snippet: str
    published: str


RESOURCES = [
    Resource(
        "Les métiers de la donnée, panorama",
        "https://blog-donnees.example.org/panorama",
        "Un tour d'horizon des métiers de la donnée.",
        "2026-11-02",
    ),
    Resource(
        "Construire une plateforme de données fiable",
        "https://ingenierie-donnees.example.org/plateforme-fiable",
        "Retours d'expérience sur les pipelines de données.",
        "2026-11-04",
    ),
    Resource(
        "Orchestrer ses traitements de données",
        "https://tutoriels-donnees.example.org/orchestration",
        "Un tutoriel sur l'orchestration de traitements.",
        "2026-11-06",
    ),
]
PICKED_RESOURCE = RESOURCES[PICKED - 1]


def resource_pick(messages: Sequence[BaseMessage]) -> str:
    """Le choix de l'Éclaireur : le résultat n° `PICKED`, avec une raison sans nombre."""
    return json.dumps({"index": PICKED, "why": WHY}, ensure_ascii=False)


def advice(messages: Sequence[BaseMessage]) -> str:
    """Le conseil du jour : deux phrases, aucun nombre."""
    return json.dumps({"sentences": SENTENCES}, ensure_ascii=False)


# --- Radar -----------------------------------------------------------------------------------

REFERENCE = "Référence interne : relevé n° 4, offre"  # suivie du numéro de l'offre
OFFER_URLS = [f"https://emplois-fictifs.example.org/offres/{n}" for n in range(1, 9)]
BLOCKED_URLS = [
    "https://connexion-requise.example.invalid/offres/1",
    "https://connexion-requise.example.invalid/offres/2",
    "https://mur-payant.example.invalid/offres/3",
]  # aucune page : le lecteur factice les dit illisibles


class Offer(NamedTuple):
    """Une offre fictive : ce que sa page dit, et ce que l'Analyste en tire."""

    title: str
    company: str
    level: str
    remote: str
    salary: str | None
    skills: tuple[tuple[str, bool], ...]  # (nom, exigée)
    tools: tuple[str, ...]


OFFERS = [
    Offer(
        "Ingénieur données",
        "Société Fictive",
        "mid_level",
        "partiel",
        "45 000 à 55 000 euros",
        (("Python", True), ("SQL", True), ("Modélisation de données", False)),
        ("Airflow", "dbt"),
    ),
    Offer(
        "Data engineer",
        "Autre SA",
        "senior",
        "total",
        None,
        (("Python", True), ("Pipelines de données", True), ("Qualité des données", False)),
        ("Airflow", "Spark"),
    ),
    Offer(
        "Ingénieure données junior",
        "Exemple Tech",
        "junior",
        "non",
        None,
        (("SQL", True), ("Python", False)),
        ("dbt",),
    ),
    Offer(
        "Ingénieur plateforme données",
        "Société Fictive",
        "senior",
        "partiel",
        None,
        (("Python", True), ("Cloud", True), ("Conteneurs", True), ("SQL", False)),
        ("Docker", "Kubernetes"),
    ),
    Offer(
        "Analytics engineer",
        "Autre SA",
        "mid_level",
        "partiel",
        None,
        (("SQL", True), ("Modélisation de données", True)),
        ("dbt",),
    ),
    Offer(
        "Ingénieur données, équipe produit",
        "Exemple Tech",
        "mid_level",
        "total",
        None,
        (("Python", True), ("Pipelines de données", True), ("Communication", False)),
        ("Spark", "Docker"),
    ),
    Offer(
        "Responsable données",
        "Société Fictive",
        "lead",
        "partiel",
        None,
        (("Gouvernance des données", True), ("Encadrement d'équipe", True), ("SQL", False)),
        (),
    ),
    Offer(
        "Ingénieure données, finance",
        "Autre SA",
        "mid_level",
        "non",
        None,
        (("Python", True), ("SQL", True), ("Qualité des données", True)),
        ("Airflow",),
    ),
]
_LOCATION = f"{ZONE} ou télétravail"


def offer_text(number: int) -> str:
    """La page de l'offre `number` (à partir de 1) : le texte que le lecteur factice rend."""
    offer = OFFERS[number - 1]
    pay = f"Rémunération : {offer.salary}.\n" if offer.salary else ""
    needs = ", ".join(name for name, _required in offer.skills)
    tools = f"Outils : {', '.join(offer.tools)}.\n" if offer.tools else ""
    return (
        f"{offer.title}, {offer.company}\n"
        f"Lieu : {_LOCATION} ({offer.remote}). {pay}"
        f"Niveau : {offer.level}.\nCompétences demandées : {needs}.\n{tools}"
        f"{REFERENCE} {number}.\n"
    )


_PAGE = re.compile(
    r'<<<CONTENU_NON_FIABLE source="offre (p\d+)">>>\n(.*?)\n<<<FIN_CONTENU_NON_FIABLE>>>',
    re.DOTALL,
)
_NUMBER = re.compile(re.escape(REFERENCE) + r" (\d+)\.")


def radar_item(local_ref: str, text: str) -> dict[str, Any]:
    """L'extraction de la page `local_ref` (`p1`…), reconnue à sa ligne de référence."""
    found = _NUMBER.search(text)
    if found is None:
        raise RuntimeError("Réponse scriptée : une page du lot n'est pas une offre du parcours.")
    offer = OFFERS[int(found.group(1)) - 1]
    return {
        "ref": local_ref,
        "is_job_posting": True,
        "title": offer.title,
        "company": offer.company,
        "level": offer.level,
        "remote": offer.remote,
        "salary": offer.salary,
        "skills": [{"name": name, "required": required} for name, required in offer.skills],
        "tools": list(offer.tools),
    }


def radar_batch(messages: Sequence[BaseMessage]) -> str:
    """Un lot de cinq offres au plus : un élément par page, chacune lue dans son encadrement."""
    pages = _PAGE.findall(prompt_of(messages))
    if not pages:
        raise RuntimeError("Réponse scriptée : le lot du radar est vide.")
    items = [radar_item(local_ref, text) for local_ref, text in pages]
    return json.dumps({"items": items}, ensure_ascii=False)


# --- Scénario et web factice -----------------------------------------------------------------


def daily_scripts() -> dict[str, list[Reply]]:
    """Les files du parcours : l'Éclaireur (ressource du brief), le Modérateur (conseil) et
    l'Analyste (lots du radar). Aucune n'est servie à un autre appel que le sien."""
    return {
        "scout": [dispatch("scout", {PICK_REQUEST: resource_pick}) for _ in range(LONG)],
        "moderator": [dispatch("moderator", {ADVICE_REQUEST: advice}) for _ in range(LONG)],
        "analyst": [dispatch("analyst", {RADAR_REQUEST: radar_batch}) for _ in range(LONG)],
    }


def radar_results() -> dict[str, list[SearchResult]]:
    """Les résultats des deux premières requêtes du relevé : onze liens, six puis cinq (le second
    mêle des offres lisibles et les trois pages bloquées)."""
    links = [*OFFER_URLS, *BLOCKED_URLS]
    queries = [search.query for search in radar_searches(ROLE, ZONE, LANGUAGES)]
    chunks = [links[:6], links[6:]]
    return {
        query: [
            SearchResult(f"Offre {url.rsplit('/', 1)[1]}", url, "Une offre fictive.", "fake", None)
            for url in chunk
        ]
        for query, chunk in zip(queries, chunks, strict=False)
    }


def script_daily_web(reader: FakeWebReader, search: FakeSearch) -> None:
    """La recherche du sujet du jour rend trois ressources dont la première n'est pas lisible
    (aucune page) ; celle du radar rend les onze liens ; les huit offres sont lisibles."""
    search.results[TOPIC_QUERY] = [
        SearchResult(item.title, item.url, item.snippet, "fake", item.published)
        for item in RESOURCES
    ]
    for item in RESOURCES[1:]:
        text = f"{item.title}. {item.snippet} Un article de fond sur le métier de la donnée."
        reader.pages[item.url] = WebDocument(
            item.url, item.title, text, None, item.published, "fr", None
        )
    search.results.update(radar_results())
    for number, url in enumerate(OFFER_URLS, start=1):
        offer = OFFERS[number - 1]
        reader.pages[url] = WebDocument(
            url, offer.title, offer_text(number), None, "2026-11-10", "fr", None
        )
