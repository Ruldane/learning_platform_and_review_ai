"""Partie `projets` du contrôle de la phase 8 : un mini projet du programme (le seul de l'unique
compte local, celui des contrôles précédents), rendu avec une description fictive et le lien d'un
dépôt public sans donnée personnelle, évalué par le Praticien avec le modèle réel.

Étape `énoncé` : un projet dont l'énoncé est écrit (`todo`, sinon `to_redo`) ; si l'énoncé est en
cours, il est attendu (10 minutes au plus : la tâche passe toutes les 15 minutes), en échec, un
seul nouvel essai est lancé ; 3 à 6 critères, 3 à 6 heures. Aucun projet éligible (tous validés,
en évaluation ou sans énoncé) : le script le dit et s'arrête. Étape `rendu` : le profil maître
validé est lu (sa version), puis le rendu part en multipart (description et lien, aucune capture).
Étape `évaluation` : la session finie en 15 minutes au plus ; verdict, critères atteints, état du
dépôt, appels du modèle et coût. Étape `suites` : projet validé, les quatre brouillons (ou
« brouillons indisponibles », issue légitime), chaque compétence du module à `prouve`, profil
inchangé, puis `profile-entry` : version + 1, le projet entré une fois, un second clic refusé
(409) ; projet à reprendre, ses critères non atteints sont nommés. Un projet validé ne se rend pas
une seconde fois : un nouveau passage prend un autre projet. Rien de ce qui est envoyé ou reçu
n'apparaît dans la sortie : seulement des étapes, des nombres, des codes et des identifiants."""

import time
from typing import Any

import httpx

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase6_steps import within
from scripts.phase7_common import expect_refusal, send, wait_session
from scripts.phase8_common import Track, cost_of, llm_calls, wait_for
from scripts.phase8_projects_rules import (
    README_URL,
    REPO_URL,
    build_description,
    check_brief,
    check_drafts,
    check_entry_added,
    check_evaluation,
    check_redo,
    check_skills,
    check_submission,
    pick_project,
    profile_view,
    readme_phrases,
    status_counts,
)

BRIEF_S = 600.0  # l'énoncé en 10 minutes au plus (la tâche des énoncés passe toutes les 15)
REVIEW_S = 900.0  # l'évaluation en 15 minutes au plus
SETTLE_S = 60.0  # le statut du projet suit la fin de la session
PAGE_TIMEOUT_S = 30.0
FALLBACK_ENTRY = "Projet de contrôle"


async def _detail(run: Run, step: str, project_id: str) -> dict[str, Any]:
    found: dict[str, Any] = await expect_ok(run, step, "GET", f"/projects/{project_id}")
    return found


async def check_statement(run: Run, st: Track) -> None:
    step = "énoncé"
    projects = await expect_ok(run, step, "GET", "/projects")
    chosen, action = pick_project(projects)
    if chosen is None:
        raise CheckFailed(
            step,
            f"Aucun projet éligible ({len(projects)} projet(s) : {status_counts(projects)}) : "
            "ni énoncé écrit ou attendu, ni énoncé à relancer. Les validés ne se rendent pas deux "
            "fois ; attends un nouveau module (tâche des énoncés) ou refais un programme.",
        )
    project_id, first = str(chosen["id"]), str(chosen["status"])
    if action == "retry":
        await expect_ok(run, step, "POST", f"/projects/{project_id}/brief")
        print("    énoncé en échec : un nouvel essai lancé (le seul)", flush=True)
    view: dict[str, Any] = {}

    async def written() -> bool:
        view.update(await _detail(run, step, project_id))
        if view["status"] == "brief_failed":
            raise CheckFailed(step, f"Énoncé du projet {project_id} en échec (brief_failed).")
        return view["status"] in ("todo", "to_redo") and view["brief"] is not None

    began = time.monotonic()
    if action != "ready":
        await wait_for(within(run, BRIEF_S), step, written, "énoncé toujours en attente", BRIEF_S)
    else:
        await written()
    if view["brief"] is None:
        raise CheckFailed(
            step, f"Projet {project_id} sans énoncé alors que son statut le dit prêt."
        )
    criteria, hours = check_brief(step, view["brief"])
    st.project, st.project_skills = view, [str(name) for name in chosen["skills"]]
    waited = f", attendu {time.monotonic() - began:.0f} s" if action != "ready" else ""
    print(
        f"    projet {project_id} (semaine {chosen['week']}, statut {first}{waited}) : "
        f"{criteria} critères, {hours} h, {len(st.project_skills)} compétence(s)",
        flush=True,
    )


async def _readme(run: Run) -> list[str]:
    """Quelques phrases du README du dépôt (pour les journaux) ; injoignable : aucune."""
    try:
        page = await run.client.get(README_URL, follow_redirects=True, timeout=PAGE_TIMEOUT_S)
        page.raise_for_status()
    except (httpx.HTTPError, httpx.InvalidURL):
        return []
    return readme_phrases(page.text)


async def check_submit(run: Run, st: Track) -> None:
    step = "rendu"
    if not st.project:
        raise CheckFailed(step, "Aucun projet choisi : « énoncé » d'abord.")
    st.profile_before = profile_view(step, await expect_ok(run, step, "GET", "/profile"))
    st.description = build_description(st.project["brief"])
    st.readme = await _readme(run)
    form = {"description": (None, st.description), "repo_url": (None, REPO_URL)}
    started = await expect_ok(run, step, "POST", f"/projects/{st.project['id']}/submit", files=form)
    st.project_session = str(started["session_id"])
    print(
        f"    rendu envoyé (description {len(st.description)} signes, un lien, 0 capture), session "
        f"{st.project_session} ; profil en version {st.profile_before[0]} "
        f"({len(st.profile_before[1])} projet(s)) ; "
        f"{len(st.readme)} phrase(s) du README relevée(s)",
        flush=True,
    )


async def check_review(run: Run, st: Track) -> None:
    step = "évaluation"
    if not st.project_session:
        raise CheckFailed(step, "Aucun rendu envoyé : « rendu » d'abord.")
    project_id, session_id, began = st.project["id"], st.project_session, time.monotonic()
    await wait_session(within(run, REVIEW_S), step, session_id, "évaluation jamais finie")
    view: dict[str, Any] = {}

    async def settled() -> bool:
        view.update(await _detail(run, step, project_id))
        return bool(view["status"] != "reviewing")

    await wait_for(run, step, settled, "projet toujours en évaluation", SETTLE_S)
    seconds = time.monotonic() - began
    st.project = view
    result = check_evaluation(step, view)
    count = check_submission(step, view, st.description)
    print(
        f"    évaluation reçue en {seconds:.0f} s : verdict {result['verdict']}, "
        f"{result['met']} critère(s) atteint(s) sur {result['total']}, dépôt {result['repo']}, "
        f"{count} rendu(s) gardé(s) ; {await llm_calls(run, session_id)} appel(s) LLM ; "
        f"{await cost_of(run, step, session_id)}",
        flush=True,
    )


def _entry_of(project: dict[str, Any]) -> dict[str, Any]:
    """L'entrée à ajouter au profil : celle du brouillon `profile_entry`, sinon une entrée fictive
    faite de l'énoncé (brouillons indisponibles)."""
    for draft in project["drafts"]:
        if draft["kind"] == "profile_entry" and draft["entry"]:
            entry: dict[str, Any] = draft["entry"]
            return entry
    brief = project["brief"]
    return {
        "name": str(project["title"])[:120] or FALLBACK_ENTRY,
        "description": str(brief["objective"])[:600],
        "achievements": [],
    }


async def _validated(run: Run, st: Track) -> None:
    step, project = "suites", st.project
    ready, to_check = check_drafts(step, project)
    print(
        f"    4 brouillons : {ready} prêt(s), {to_check} à vérifier"
        if ready + to_check
        else "    brouillons indisponibles (issue légitime, l'évaluation est gardée)",
        flush=True,
    )
    graph = await expect_ok(run, step, "GET", "/skills/graph")
    print(f"    {check_skills(step, graph, st.project_skills)} compétence(s) à prouve", flush=True)
    before = profile_view(step, await expect_ok(run, step, "GET", "/profile"))
    if before[0] != st.profile_before[0] or project["profile_version"] is not None:
        raise CheckFailed(step, "Le profil maître a bougé avant `profile-entry`.")
    entry = _entry_of(project)
    path = f"/projects/{project['id']}/profile-entry"
    added = await expect_ok(run, step, "POST", path, json=entry)
    after = profile_view(step, await expect_ok(run, step, "GET", "/profile"))
    check_entry_added(step, before, after, str(entry["name"]), added["profile_version"])
    again = await send(run, step, "POST", path, json=entry)
    expect_refusal(again, step, "Second ajout", 409, "entry_already_added")
    st.project = added
    print(
        f"    profil {before[0]} -> {after[0]}, projet entré une fois ; second ajout refusé",
        flush=True,
    )


async def _to_redo(run: Run, st: Track) -> None:
    step, project = "suites", st.project
    unmet = check_redo(step, project)
    current = profile_view(step, await expect_ok(run, step, "GET", "/profile"))
    if current[0] != st.profile_before[0] or project["profile_version"] is not None:
        raise CheckFailed(step, "Le profil maître a bougé sans validation du projet.")
    print(
        f"    projet à reprendre : {unmet} critère(s) non atteint(s), nommés ; aucun brouillon ; "
        f"profil inchangé (version {current[0]}) ; le projet reste éligible",
        flush=True,
    )


async def check_outcome(run: Run, st: Track) -> None:
    if not st.project or not st.project.get("evaluation"):
        raise CheckFailed("suites", "Aucune évaluation reçue : « évaluation » d'abord.")
    await (_validated if st.project["status"] == "validated" else _to_redo)(run, st)
