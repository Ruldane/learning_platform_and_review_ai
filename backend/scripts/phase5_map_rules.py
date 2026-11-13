"""Règles de la carte de compétences du contrôle de fin de phase 5 (`check_phase5`), en fonctions
pures : la session guidée et le quiz mettent à jour la carte (preuves et niveau des compétences du
module, F15, F26). Les messages ne portent que des étapes, des nombres, des codes et des rangs :
jamais le nom d'une compétence ni le libellé d'une preuve."""

import re
import unicodedata
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from scripts.phase4_rules import CheckFailed

EVIDENCE_MAX = 20  # preuves gardées par compétence (les plus récentes) : le compte plafonne
STUDY_LEVELS = ("en_cours", "valide", "prouve")  # niveau minimal après une session guidée
QUIZ_LEVELS = ("valide", "prouve")  # niveau après un quiz réussi (≥ 80 %)
_SPACES = re.compile(r"\s+")
_EDGE = " .,;:!?'\"«»()[]{}-_/\\"


def norm_skill(name: str) -> str:
    """Même clé que le back : sans accents, en minuscules, espaces ramassés, bords nettoyés."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return _SPACES.sub(" ", plain.casefold()).strip(_EDGE)


@dataclass(frozen=True)
class SkillState:
    """Une compétence sur la carte : son id (vide si elle n'y est pas encore), niveau et preuves."""

    skill_id: str
    level: str | None
    evidence: int


def module_skill_names(program: dict[str, Any], module_id: str, step: str) -> list[str]:
    """Les compétences du module, telles que le programme les nomme."""
    for week in program["weeks"]:
        for module in week["modules"]:
            if module["id"] == module_id:
                return [str(name) for name in module["skills"]]
    raise CheckFailed(step, f"Module {module_id} absent du programme.")


def read_states(graph: dict[str, Any], names: list[str]) -> dict[str, SkillState]:
    """L'état de chaque compétence du module (clé = nom normalisé) : une compétence que la carte
    ne connaît pas encore n'a ni niveau ni preuve."""
    nodes = {norm_skill(node["name"]): node for node in graph["nodes"]}
    found: dict[str, SkillState] = {}
    for name in names:
        key = norm_skill(name)
        node = nodes.get(key)
        found[key] = SkillState("", None, 0)
        if node is not None:
            found[key] = SkillState(node["id"], node["level"], int(node["evidence_count"]))
    return found


def check_states(
    step: str,
    before: Mapping[str, SkillState],
    after: Mapping[str, SkillState],
    *,
    studied: Collection[str],
    validated: Collection[str],
) -> None:
    """Les compétences du module étudié (`studied`) : niveau d'au moins `en_cours` et une preuve
    de plus ; celles du module dont le quiz est réussi (`validated`, le même ou un autre) :
    `valide` au moins et une preuve de plus (deux pour une compétence dans les deux). Le compte de
    preuves plafonne à 20. Les autres compétences ne sont pas contrôlées."""
    if not studied:
        raise CheckFailed(step, "Le module n'a aucune compétence.")
    keys = [key for key in before if key in studied or key in validated]
    for rank, key in enumerate(keys, start=1):
        old, new = before[key], after.get(key)
        if new is None or not new.skill_id:
            raise CheckFailed(step, f"Compétence n° {rank} du module absente de la carte.")
        wanted = QUIZ_LEVELS if key in validated else STUDY_LEVELS
        if new.level not in wanted:
            raise CheckFailed(
                step, f"Compétence n° {rank} au niveau {new.level} : {' ou '.join(wanted)} attendu."
            )
        need = min(old.evidence + (key in studied) + (key in validated), EVIDENCE_MAX)
        if new.evidence < need:
            raise CheckFailed(
                step,
                f"Compétence n° {rank} : {new.evidence} preuve(s), {need} au moins attendue(s) "
                f"({old.evidence} avant).",
            )


def check_detail(
    step: str, detail: dict[str, Any], *, study_id: str | None, quiz_id: str | None
) -> None:
    """La fiche de la compétence cite la session (si elle a été étudiée) et le quiz (s'il est
    réussi) par leur adresse."""
    urls = {(e["kind"], e["url"]) for e in detail["evidence"]}
    if study_id and ("study", f"/etudier/session/{study_id}") not in urls:
        raise CheckFailed(step, f"Preuve de la session {study_id} absente de la compétence.")
    if quiz_id and ("quiz", f"/etudier/quiz/{quiz_id}") not in urls:
        raise CheckFailed(step, f"Preuve du quiz {quiz_id} absente de la compétence.")


def check_history(step: str, history: dict[str, Any], weeks: set[date], skills: int) -> None:
    """Le dernier point est la semaine en cours (lundi local, avant ou après un minuit) et compte
    au moins les compétences du module ; son score n'est pas nul."""
    points = history["points"]
    if not points:
        raise CheckFailed(step, "Aucun point dans l'historique des compétences.")
    last = points[-1]
    if date.fromisoformat(last["week_start"]) not in weeks:
        raise CheckFailed(step, f"Dernier point du {last['week_start']} : pas la semaine en cours.")
    counted = sum(int(n) for n in last["counts"].values())
    if counted < skills:
        raise CheckFailed(step, f"{counted} compétence(s) sur le dernier point, {skills} au moins.")
    if int(last["score"]) <= 0:
        raise CheckFailed(step, "Score nul sur le dernier point de l'historique.")
