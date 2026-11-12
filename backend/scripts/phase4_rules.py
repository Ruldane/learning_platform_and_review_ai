"""Règles du contrôle de fin de phase 4 (`check_phase4`), en fonctions pures : chacune lit des
événements ou des réponses de l'API déjà reçus et lève `CheckFailed` quand une règle n'est pas
tenue. Les messages ne portent que des étapes, des nombres et des identifiants."""

from typing import Any

MIN_SCORED_SOURCES = 8
DEBATERS = frozenset({"strategist", "practitioner", "scout", "skeptic"})
LESSON_WEEKS = (1, 2)
MIN_PROPOSALS, MAX_PROPOSALS = 2, 3
MIN_RESOURCES, MAX_RESOURCES = 3, 6
MAX_LESSON_ATTEMPTS = 3  # `lessons.service.production.MAX_ATTEMPTS`


class CheckFailed(Exception):
    """Étape ratée : `step` et un message en français (jamais une donnée de January)."""

    def __init__(self, step: str, message: str) -> None:
        super().__init__(message)
        self.step = step


def debate_rounds_of(events: list[dict[str, Any]]) -> dict[int, set[str]]:
    """Débatteurs qui ont parlé à chaque tour (étape `positions` = tour 1, `tour-N` = tour N)."""
    steps: dict[str, str] = {}
    rounds: dict[int, set[str]] = {}
    for event in events:
        agent = event.get("agent") or ""
        if event["type"] == "agent.started":
            steps[agent] = event["payload"]["step"]
        elif event["type"] == "agent.message" and agent in DEBATERS:
            step = steps.get(agent, "")
            number = 1 if step == "positions" else int(step[5:]) if step[5:].isdigit() else 0
            if number:
                rounds.setdefault(number, set()).add(agent)
    return rounds


def _check_debate(events: list[dict[str, Any]], debate_rounds: int) -> None:
    rounds = debate_rounds_of(events)
    if not 2 <= len(rounds) <= 1 + debate_rounds:
        raise CheckFailed("conseil", f"{len(rounds)} tour(s) de débat (réglage : {debate_rounds}).")
    partial = sorted(n for n, agents in rounds.items() if agents != DEBATERS)
    if partial:
        raise CheckFailed("conseil", f"Tours incomplets (4 débatteurs attendus) : {partial}.")


def check_council_events(events: list[dict[str, Any]], debate_rounds: int) -> None:
    """Sources notées, tours complets, tableau dessiné, 2 à 3 propositions."""
    found = [e["payload"] for e in events if e["type"] == "source.found"]
    scored = {p.get("source_id") or p["url"] for p in found if p.get("score") is not None}
    if len(scored) < MIN_SCORED_SOURCES:
        raise CheckFailed("conseil", f"{len(scored)} source(s) notée(s) : 8 au moins.")
    _check_debate(events, debate_rounds)
    if not any(e["type"] == "board.update" for e in events):
        raise CheckFailed("conseil", "Aucun tableau dessiné (board.update).")
    ready = sum(e["type"] == "proposal.ready" for e in events)
    if not MIN_PROPOSALS <= ready <= MAX_PROPOSALS:
        raise CheckFailed("conseil", f"{ready} proposition(s) : 2 à 3 attendues.")


def week_problems(week: dict[str, Any], cap: int) -> list[str]:
    """Charge sous le plafond, une tâche de pratique, un quiz le dernier jour de la semaine."""
    tasks = [task for module in week["modules"] for task in module["tasks"]]
    rank = week["rank"]
    problems: list[str] = []
    if week["load_minutes"] > cap:
        problems.append(f"semaine {rank} : {week['load_minutes']} min pour {cap} au plus")
    if not any(task["type"] == "pratiquer" for task in tasks):
        problems.append(f"semaine {rank} sans pratique")
    last_day = max((task["planned_date"] for task in tasks), default=None)
    if not any(t["type"] == "quiz" and t["planned_date"] == last_day for t in tasks):
        problems.append(f"semaine {rank} ne finit pas par un quiz")
    return problems


def check_program_draft(program: dict[str, Any]) -> dict[str, int]:
    """Brouillon d'au moins 2 semaines qui tient ses règles ; rend les modules des semaines 1 et
    2 (id -> rang de la semaine), ceux dont les leçons sont attendues."""
    if program["status"] != "draft" or not program["weeks"]:
        raise CheckFailed("programme", f"Programme {program['status']}, sans brouillon à valider.")
    ranks = {week["rank"] for week in program["weeks"]}
    if not set(LESSON_WEEKS) <= ranks:
        raise CheckFailed("programme", f"Programme de moins de 2 semaines ({len(ranks)}).")
    problems = [p for w in program["weeks"] for p in week_problems(w, program["cap_minutes"])]
    if problems:
        raise CheckFailed("programme", f"Règles du programme non tenues : {'; '.join(problems)}.")
    modules = {
        module["id"]: week["rank"]
        for week in program["weeks"]
        if week["rank"] in LESSON_WEEKS
        for module in week["modules"]
    }
    if {rank for rank in modules.values()} != set(LESSON_WEEKS):
        raise CheckFailed("programme", "Une des semaines 1 et 2 n'a aucun module.")
    return modules


def lessons_done(lessons: list[dict[str, Any]], modules: dict[str, int]) -> bool:
    """Vrai quand chaque module attendu a sa leçon prête avec son PDF ; échec dès qu'une leçon
    attendue est en échec après ses 3 essais (avant : elle sera relancée, donc encore en cours,
    D98). Une leçon est rangée « prête » avant le rendu de son PDF."""
    expected = [lesson for lesson in lessons if lesson["module_id"] in modules]
    failed = [
        lesson["id"]
        for lesson in expected
        if lesson["status"] == "failed" and lesson["attempts"] >= MAX_LESSON_ATTEMPTS
    ]
    if failed:
        raise CheckFailed("leçons", f"Leçon(s) en échec : {', '.join(failed)}.")
    done = {
        lesson["module_id"]
        for lesson in expected
        if lesson["status"] == "ready" and lesson["pdf_available"]
    }
    return bool(modules) and done == set(modules)


def check_lesson_files(lesson_id: str, pdf: bytes, resources: int) -> None:
    """Le PDF de la leçon en est un ; 3 à 6 ressources."""
    if not pdf.startswith(b"%PDF"):
        raise CheckFailed("leçons", f"Leçon {lesson_id} : le PDF n'en est pas un.")
    if not MIN_RESOURCES <= resources <= MAX_RESOURCES:
        raise CheckFailed(
            "leçons", f"Leçon {lesson_id} : {resources} ressource(s), 3 à 6 attendues."
        )


def check_export_files(pdf: bytes, ics: str) -> None:
    """L'export PDF du programme en est un, son export .ics est un calendrier."""
    if not pdf.startswith(b"%PDF"):
        raise CheckFailed("exports", "L'export PDF du programme n'est pas un PDF.")
    if "BEGIN:VCALENDAR" not in ics:
        raise CheckFailed("exports", "L'export .ics du programme n'est pas un calendrier.")
