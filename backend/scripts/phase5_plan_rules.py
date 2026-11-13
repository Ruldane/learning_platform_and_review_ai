"""Règles du planning, de la capture et du journal du contrôle de fin de phase 5 (`check_phase5`),
en fonctions pures : la replanification de la semaine (F13), le bilan hebdomadaire planifié et le
journal (F18). Les messages ne portent que des étapes, des nombres, des dates, des codes et des
identifiants : jamais un titre de tâche, un texte capturé ni une adresse."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from scripts.phase4_rules import CheckFailed

WEEK_MINUTES = 300  # « cette semaine je n'ai que 5 heures »
REPLAN_MESSAGE = "cette semaine je n'ai que 5 heures"
ROOM_MINUTES = (
    65  # la place d'une pratique (45 min) et du quiz (20 min), au-delà des minutes faites
)
MAX_MINUTES = 10080  # une semaine entière : borne du champ
WEEKLY_LAUNCH_S = 16 * 60  # tâche planifiée toutes les 15 minutes, plus une minute de marge
DAYS = 7
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def week_cap(minutes: int) -> int:
    """Le plafond de la semaine quand January n'a que `minutes` : 85 %, arrondi vers le bas (255
    pour 5 heures)."""
    return minutes * 85 // 100


def capped_week(program: dict[str, Any], today: date) -> date | None:
    """Le lundi de la semaine plafonnée par January : celle d'aujourd'hui, ou la première du
    programme s'il n'a pas commencé."""
    starts = sorted(date.fromisoformat(week["start_date"]) for week in program["weeks"])
    begun = [start for start in starts if start <= today]
    return begun[-1] if begun else (starts[0] if starts else None)


def feasible_minutes(program: dict[str, Any], today: date) -> int:
    """Les minutes à dire au Stratège : 300 (« 5 heures ») quand la semaine plafonnée tient encore
    une pratique et un quiz au-delà de ce qui est déjà fait, sinon le plus petit multiple de 15
    qui les tient (le back refuse une semaine sans cette place : version `impossible`). La semaine
    plafonnée est celle d'aujourd'hui, ou la première du programme s'il n'a pas commencé."""
    first = capped_week(program, today)
    if first is None:
        return WEEK_MINUTES
    done = sum(
        int(task["minutes"])
        for week in program["weeks"]
        for module in week["modules"]
        for task in module["tasks"]
        if task["status"] == "done"
        and first <= date.fromisoformat(task["planned_date"]) < first + timedelta(days=DAYS)
    )
    minutes = WEEK_MINUTES
    while week_cap(minutes) < done + ROOM_MINUTES and minutes < MAX_MINUTES:
        minutes += 15
    return minutes


def check_nothing_to_change(program: dict[str, Any], today: date, cap_week: int) -> None:
    """Version `empty` : le plan tient déjà (replanification déjà acceptée, par exemple) ; la
    semaine plafonnée ne doit alors pas dépasser le plafond de January, sinon le back a eu tort."""
    first = capped_week(program, today)
    for week in program["weeks"]:
        if date.fromisoformat(week["start_date"]) == first and week["load_minutes"] > cap_week:
            raise CheckFailed(
                "replanification",
                f"Rien à changer, mais la semaine {week['rank']} compte {week['load_minutes']} min "
                f"(plafond {cap_week}).",
            )


def check_pending(
    version: dict[str, Any], program: dict[str, Any], session_id: str, cap_week: int
) -> None:
    """La proposition en attente : version `replan` `pending` de cette session, un avant / après,
    une seule semaine plafonnée par January (`cap_week`, 255 minutes pour 5 heures), aucune
    au-delà de son plafond ni de celui du programme."""
    step = "replanification"
    if version["status"] != "pending" or version["kind"] != "replan":
        raise CheckFailed(
            step, f"Version {version['version']} {version['kind']}/{version['status']} : "
            "proposition `pending` attendue."
        )  # fmt: skip
    if version["session_id"] != session_id:
        raise CheckFailed(
            step, f"Proposition de la session {version['session_id']}, pas {session_id}."
        )
    if version["diff"] is None or not version["week_loads"]:
        raise CheckFailed(step, "Proposition sans avant / après.")
    cap = int(program["cap_minutes"])
    capped = [row for row in version["week_loads"] if row["cap"] == cap_week]
    if len(capped) != 1:
        raise CheckFailed(
            step, f"{len(capped)} semaine(s) plafonnée(s) à {cap_week} min : une seule."
        )
    for row in version["week_loads"]:
        if row["after"] > min(row["cap"], cap):
            raise CheckFailed(
                step,
                f"Semaine {row['rank']} à {row['after']} min, plafond {min(row['cap'], cap)}.",
            )


def capped_start(version: dict[str, Any], cap_week: int) -> date:
    """Le lundi de la semaine plafonnée par January."""
    row = next(r for r in version["week_loads"] if r["cap"] == cap_week)
    return date.fromisoformat(row["start_date"])


def check_accepted(
    version: dict[str, Any], program: dict[str, Any], *, before: int, capped: date, cap_week: int
) -> None:
    """Acceptée : version `accepted` qui devient celle du programme, aucune semaine au-delà du
    plafond du programme et la semaine plafonnée à `cap_week` minutes au plus."""
    step = "replanification"
    if version["status"] != "accepted" or not version["accepted_at"]:
        raise CheckFailed(
            step, f"Version {version['version']} {version['status']} : `accepted` attendu."
        )
    # Les versions sont numérotées dans l'ordre d'écriture, closes comprises (`empty`, `refused`,
    # `superseded`) : le programme prend le numéro de la version acceptée, qui est > `before` ; +1
    # exactement quand aucune proposition n'a été écrite entre-temps.
    if not (program["version"] == version["version"] and version["version"] > before):
        raise CheckFailed(
            step, f"Programme à la version {program['version']}, version acceptée "
            f"{version['version']}, après la {before}."
        )  # fmt: skip
    cap = program["cap_minutes"]
    for week in program["weeks"]:
        if week["load_minutes"] > cap:
            raise CheckFailed(
                step,
                f"Semaine {week['rank']} à {week['load_minutes']} min, plafond {cap}.",
            )
        if date.fromisoformat(week["start_date"]) == capped and week["load_minutes"] > cap_week:
            raise CheckFailed(
                step, f"Semaine {week['rank']} à {week['load_minutes']} min, plafond {cap_week}."
            )


def review_blocker(week_starts: Iterable[date], today: date) -> str | None:
    """Pourquoi le bilan d'aujourd'hui ne peut pas s'écrire (le back relit la semaine qui finit
    le dernier dimanche, ou la précédente, et exige qu'elle touche le programme et qu'il reste
    une semaine après) ; `None` s'il le peut. Le message dit à partir de quel jour réessayer."""
    starts = sorted(week_starts)
    reviewed = today - timedelta(days=DAYS - 1)
    reviewed -= timedelta(days=reviewed.weekday())  # lundi de la semaine relue
    first, last = starts[0], starts[-1]
    if first >= reviewed + timedelta(days=DAYS):
        ready = first + timedelta(days=DAYS - 1)
        return (
            f"Le programme commence le {first} : la semaine relue ({reviewed}) n'en fait pas "
            f"partie. Relance ce contrôle à partir du {ready} (dimanche de la semaine 1)."
        )
    if last <= reviewed:
        return f"Aucune semaine après la semaine relue ({reviewed}) : rien à replanifier."
    return None


def local_target(now: datetime) -> tuple[str, str]:
    """Le réglage du bilan : le jour local et l'heure locale moins une minute."""
    target = now - timedelta(minutes=1)
    return WEEKDAYS[target.weekday()], target.strftime("%H:%M")


@dataclass(frozen=True)
class JournalWant:
    """Ce que le journal doit montrer à la fin du passage."""

    study_id: str
    attempt_id: str  # vide : quiz bloqué, aucune tentative ce jour-là, n'importe quelle entrée
    review_id: str | None  # None : bilan déjà écrit plus tôt, n'importe quelle entrée convient
    captures: list[str] = field(default_factory=list)  # sessions d'agents des captures


def check_journal(entries: list[dict[str, Any]], want: JournalWant) -> None:
    """Une entrée de chaque genre, reliée à ce que ce passage a fait."""
    step = "journal"

    def has(kind: str, link: str, value: str) -> bool:
        return any(e["kind"] == kind and e["links"][link] == value for e in entries)

    if not has("study_session", "study_session_id", want.study_id):
        raise CheckFailed(step, f"Aucune entrée `study_session` pour la session {want.study_id}.")
    if want.attempt_id and not has("quiz", "quiz_attempt_id", want.attempt_id):
        raise CheckFailed(step, f"Aucune entrée `quiz` pour la tentative {want.attempt_id}.")
    if not want.attempt_id and not any(e["kind"] == "quiz" for e in entries):
        raise CheckFailed(step, "Aucune entrée `quiz` : le quiz bloqué a une tentative ratée.")
    for session_id in want.captures:
        if not has("capture", "session_id", session_id):
            raise CheckFailed(step, f"Aucune entrée `capture` pour la session {session_id}.")
    reviews = [e for e in entries if e["kind"] == "weekly_review"]
    if not reviews or (want.review_id and all(e["id"] != want.review_id for e in reviews)):
        raise CheckFailed(step, "Aucune entrée `weekly_review` pour le bilan de ce passage.")
