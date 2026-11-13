"""Règles de la carte de compétences du contrôle de fin de phase 5 (`check_phase5`), en fonctions
pures : la session guidée et le quiz mettent à jour la carte (preuves et niveau des compétences du
module, F15, F26). Les messages ne portent que des étapes, des nombres, des codes et des rangs :
jamais le nom d'une compétence ni le libellé d'une preuve."""

import re
import unicodedata
from collections.abc import Mapping
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
    step: str, before: Mapping[str, SkillState], after: Mapping[str, SkillState], *, passed: bool
) -> None:
    """Chaque compétence du module : niveau d'au moins `en_cours` (`valide` après un quiz réussi)
    et au moins une preuve de plus (deux après un quiz réussi), le compte plafonnant à 20."""
    if not before:
        raise CheckFailed(step, "Le module n'a aucune compétence.")
    wanted = QUIZ_LEVELS if passed else STUDY_LEVELS
    for rank, (key, old) in enumerate(before.items(), start=1):
        new = after.get(key)
        if new is None or not new.skill_id:
            raise CheckFailed(step, f"Compétence n° {rank} du module absente de la carte.")
        if new.level not in wanted:
            raise CheckFailed(
                step, f"Compétence n° {rank} au niveau {new.level} : {' ou '.join(wanted)} attendu."
            )
        need = min(old.evidence + 1 + int(passed), EVIDENCE_MAX)
        if new.evidence < need:
            raise CheckFailed(
                step,
                f"Compétence n° {rank} : {new.evidence} preuve(s), {need} au moins attendue(s) "
                f"({old.evidence} avant).",
            )


def check_detail(
    step: str, detail: dict[str, Any], *, study_id: str, quiz_id: str, passed: bool
) -> None:
    """La fiche de la compétence cite la session (et le quiz, s'il est réussi) par leur adresse."""
    urls = {(e["kind"], e["url"]) for e in detail["evidence"]}
    if ("study", f"/etudier/session/{study_id}") not in urls:
        raise CheckFailed(step, f"Preuve de la session {study_id} absente de la compétence.")
    if passed and ("quiz", f"/etudier/quiz/{quiz_id}") not in urls:
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
