"""Règles de la partie `projets` du contrôle de la phase 8 (`check_phase8`), en fonctions pures :
chacune lit une réponse de l'API déjà reçue (Portfolio, projet, carte des compétences, profil) et
lève `CheckFailed` quand une règle n'est pas tenue. Les messages ne portent que des étapes, des
nombres, des rangs et des codes : jamais un titre, un critère, un brouillon, un lien ni la phrase
d'un retour."""

import re
from typing import Any

from scripts.phase4_rules import CheckFailed
from scripts.phase5_map_rules import norm_skill

# Le dépôt public rendu, sans donnée personnelle : un projet libre très connu, dont le README se
# lit sans connexion (la page du dépôt, lue par le back, et le README brut, relu ici pour les
# journaux).
REPO_URL = "https://github.com/psf/requests"
README_URL = "https://raw.githubusercontent.com/psf/requests/HEAD/README.md"
DRAFT_KINDS = ("cv_line", "linkedin_post", "profile_entry", "readme_plan")
MIN_CRITERIA, MAX_CRITERIA = 3, 6
MIN_HOURS, MAX_HOURS = 3, 6
DESCRIPTION_MAX = 3900  # la limite du back est 4 000
MIN_TEXT = 4  # un texte plus court qu'ici n'est pas cherché dans les journaux (trop banal)
MIN_SENTENCE = 12  # un commentaire ou un retour plus court n'est pas cherché non plus
README_PHRASES = 5
README_MIN = 40  # une ligne du README plus courte n'est pas gardée
# Du plus prêt au moins prêt : un énoncé écrit d'abord, puis un énoncé attendu, puis à relancer.
_PICK_ORDER = (
    ("todo", "ready"),
    ("to_redo", "ready"),
    ("brief_pending", "wait"),
    ("brief_failed", "retry"),
)
_MARKDOWN = re.compile(r"[#*>`_|]+")
_NOISE = ("http", "[", "![", "<")  # liens, badges, balises : pas des phrases


def pick_project(projects: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    """Le projet à rendre et ce qu'il faut en faire : `ready` (énoncé écrit, statut `todo` d'abord
    puis `to_redo`), `wait` (énoncé en cours), `retry` (énoncé en échec : un seul nouvel essai) ;
    dans chaque cas le plus tôt du programme (semaine, rang). `(None, "none")` : aucun éligible
    (validés, en évaluation et énoncés absents ne le sont pas)."""
    for status, action in _PICK_ORDER:
        found = [project for project in projects if project["status"] == status]
        if found:
            found.sort(key=lambda p: (p["week"] or 99, p["rank"] or 99, str(p["id"])))
            return found[0], action
    return None, "none"


def status_counts(projects: list[dict[str, Any]]) -> str:
    """Les projets par statut (« todo 2, validated 1 ») : des codes et des nombres."""
    counts: dict[str, int] = {}
    for project in projects:
        counts[str(project["status"])] = counts.get(str(project["status"]), 0) + 1
    return ", ".join(f"{status} {number}" for status, number in sorted(counts.items())) or "aucun"


def check_brief(step: str, brief: dict[str, Any] | None) -> tuple[int, int]:
    """L'énoncé est complet : 3 à 6 critères, 3 à 6 heures. Rend `(critères, heures)`."""
    if not brief:
        raise CheckFailed(step, "Énoncé absent du projet.")
    blank = [
        key
        for key in ("title", "context", "objective", "deliverable")
        if not str(brief[key]).strip()
    ]
    if blank:
        raise CheckFailed(step, f"Énoncé : rubrique(s) vide(s) ({', '.join(blank)}).")
    criteria = brief["criteria"]
    if not MIN_CRITERIA <= len(criteria) <= MAX_CRITERIA:
        raise CheckFailed(
            step, f"{len(criteria)} critère(s), {MIN_CRITERIA} à {MAX_CRITERIA} attendus."
        )
    if any(not str(criterion).strip() for criterion in criteria):
        raise CheckFailed(step, "Un critère de l'énoncé est vide.")
    if not MIN_HOURS <= int(brief["hours"]) <= MAX_HOURS:
        raise CheckFailed(
            step, f"{brief['hours']} h annoncées, {MIN_HOURS} à {MAX_HOURS} h attendues."
        )
    return len(criteria), int(brief["hours"])


def build_description(brief: dict[str, Any]) -> str:
    """La description fictive du rendu, écrite à partir de l'énoncé lui-même : aucune donnée
    personnelle, et chaque critère y est dit traité (le verdict reste celui du modèle)."""
    lines = [
        f"Rendu du projet « {brief['title']} » (exercice de contrôle, texte fictif).",
        f"Livrable : {brief['deliverable']}. Objectif visé : {brief['objective']}",
        "Ce que j'ai réalisé, critère par critère :",
    ]
    for rank, criterion in enumerate(brief["criteria"], 1):
        lines.append(f"{rank}. {criterion} Traité dans le dépôt lié, avec ses tests et son README.")
    return "\n".join(lines)[:DESCRIPTION_MAX]


def check_evaluation(step: str, project: dict[str, Any]) -> dict[str, Any]:
    """L'évaluation reçue : un résultat par critère (rangs 1 à N), le verdict d'accord avec le
    nombre de critères atteints et avec le statut du projet, le dépôt lu. Rend ses nombres."""
    evaluation = project["evaluation"]
    if evaluation is None:
        raise CheckFailed(step, "Aucune évaluation sur le projet.")
    total = len(project["brief"]["criteria"])
    ranks = sorted(int(result["index"]) for result in evaluation["results"])
    if ranks != list(range(1, total + 1)):
        raise CheckFailed(
            step, f"{len(ranks)} résultat(s) pour {total} critère(s), rangs inexacts."
        )
    met = sum(1 for result in evaluation["results"] if result["met"])
    verdict = evaluation["verdict"]
    if (verdict == "validated") != (met == total):
        raise CheckFailed(
            step, f"Verdict « {verdict} » incohérent avec {met} critère(s) sur {total}."
        )
    if project["status"] != verdict:
        raise CheckFailed(step, f"Statut « {project['status']} » pour un verdict « {verdict} ».")
    if evaluation["repo_status"] != "read":
        raise CheckFailed(
            step, f"Dépôt « {evaluation['repo_status']} » : le lien rendu devait se lire."
        )
    if not str(evaluation["feedback"]).strip():
        raise CheckFailed(step, "Retour écrit du Praticien vide.")
    return {"verdict": verdict, "met": met, "total": total, "repo": evaluation["repo_status"]}


def check_submission(step: str, project: dict[str, Any], description: str) -> int:
    """Le dernier rendu gardé est celui qui vient d'être envoyé (lien, description, aucune capture).
    Rend le nombre de rendus du projet."""
    submissions = project["submissions"]
    if not submissions:
        raise CheckFailed(step, "Aucun rendu gardé sur le projet.")
    last = submissions[-1]
    if last["repo_url"] != REPO_URL or last["description"] != description.strip():
        raise CheckFailed(step, "Le dernier rendu gardé n'est pas celui qui vient d'être envoyé.")
    if int(last["screenshots"]) != 0:
        raise CheckFailed(step, f"{last['screenshots']} capture(s) gardée(s), aucune envoyée.")
    return len(submissions)


def check_drafts(step: str, project: dict[str, Any]) -> tuple[int, int]:
    """Projet validé : les quatre brouillons, un de chaque sorte, `ready` ou `to_check`, ou aucun
    (« brouillons indisponibles », issue légitime). Rend `(prêts, à vérifier)`, `(0, 0)` sans."""
    drafts = project["drafts"]
    if not drafts:
        return 0, 0
    if sorted(draft["kind"] for draft in drafts) != sorted(DRAFT_KINDS):
        raise CheckFailed(step, f"{len(drafts)} brouillon(s) : un de chaque sorte attendu.")
    if any(draft["status"] not in ("ready", "to_check") for draft in drafts):
        raise CheckFailed(step, "Brouillon d'un état inconnu.")
    if any(not str(draft["content"]).strip() and not draft["entry"] for draft in drafts):
        raise CheckFailed(step, "Un brouillon est vide.")
    ready = sum(1 for draft in drafts if draft["status"] == "ready")
    return ready, len(drafts) - ready


def check_skills(step: str, graph: dict[str, Any], names: list[str]) -> int:
    """Chaque compétence du module est sur la carte au niveau `prouve`. Rend leur nombre."""
    if not names:
        raise CheckFailed(step, "Module sans compétence : rien à prouver.")
    nodes = {norm_skill(node["name"]): node for node in graph["nodes"]}
    short = [name for name in names if (nodes.get(norm_skill(name)) or {}).get("level") != "proven"]
    if short:
        raise CheckFailed(step, f"{len(short)} compétence(s) sur {len(names)} pas à « prouve ».")
    return len(names)


def check_redo(step: str, project: dict[str, Any]) -> int:
    """Projet à reprendre : aucun brouillon, les critères non atteints sont nommés (chacun avec son
    texte) ; rend leur nombre (jamais leur texte)."""
    if project["drafts"]:
        raise CheckFailed(step, "Un projet à reprendre ne porte aucun brouillon.")
    unmet = [result for result in project["evaluation"]["results"] if not result["met"]]
    if not unmet:
        raise CheckFailed(step, "Projet à reprendre sans aucun critère non atteint.")
    if any(not str(result["criterion"]).strip() for result in unmet):
        raise CheckFailed(step, "Un critère non atteint n'est pas nommé.")
    return len(unmet)


def profile_view(step: str, state: dict[str, Any]) -> tuple[int, list[str]]:
    """La version du profil validé et les noms de ses projets ; un profil validé est exigé."""
    validated = state.get("validated")
    if validated is None:
        raise CheckFailed(step, "Aucun profil maître validé : `profile-entry` serait refusé.")
    if state.get("draft") is not None:
        raise CheckFailed(step, "Un brouillon de profil attend : `profile-entry` serait refusé.")
    return int(validated["version"]), [str(p["name"]) for p in validated["data"]["projects"]]


def check_entry_added(
    step: str, before: tuple[int, list[str]], after: tuple[int, list[str]], name: str, recorded: Any
) -> None:
    """Après `profile-entry` : version + 1 exactement, le projet ajouté une seule fois, et noté sur
    le projet."""
    if after[0] != before[0] + 1:
        raise CheckFailed(step, f"Profil en version {after[0]}, {before[0] + 1} attendue.")
    if len(after[1]) != len(before[1]) + 1 or after[1].count(name) != before[1].count(name) + 1:
        raise CheckFailed(step, "Le projet n'est pas entré une seule fois dans le profil.")
    if recorded != after[0]:
        raise CheckFailed(step, "Le projet ne note pas la version du profil qui le porte.")


def readme_phrases(text: str) -> list[str]:
    """Quelques phrases du README (lignes de prose d'au moins 40 signes) : le back ne les écrit
    jamais dans ses journaux."""
    found: list[str] = []
    for raw in text.splitlines():
        line = " ".join(_MARKDOWN.sub(" ", raw).split())
        if (
            len(line) >= README_MIN
            and not any(mark in line for mark in _NOISE)
            and line not in found
        ):
            found.append(line)
    return found[:README_PHRASES]


def project_extras(project: dict[str, Any], description: str, readme: list[str]) -> list[str]:
    """Les textes de ce passage que les journaux ne portent jamais : titre, énoncé, critères, rendu
    (description et lien), retour, commentaires, brouillons et phrases du README."""
    brief, evaluation = project.get("brief") or {}, project.get("evaluation") or {}
    short: list[Any] = [project.get("title"), description, REPO_URL, brief.get("title")]
    long: list[Any] = [
        brief.get("context"),
        brief.get("objective"),
        *(brief.get("constraints") or []),
        *(brief.get("criteria") or []),
        evaluation.get("feedback"),
        *readme,
    ]
    for result in evaluation.get("results") or []:
        long += [result.get("criterion"), result.get("comment")]
    for draft in project.get("drafts") or []:
        entry = draft.get("entry") or {}
        long += [draft.get("content"), entry.get("name"), entry.get("description")]
        long += list(entry.get("achievements") or [])
    texts = {str(t).strip() for t in short if t and len(str(t).strip()) >= MIN_TEXT}
    texts |= {str(t).strip() for t in long if t and len(str(t).strip()) >= MIN_SENTENCE}
    return sorted(texts)
