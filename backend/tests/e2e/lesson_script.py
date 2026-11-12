"""Réponses scriptées de la suite du Conseil (parcours de bout en bout, SPEC 18.2) : le programme
du Stratège (2 semaines × 1 module), puis, pour chaque leçon, la recherche de l'Éclaireur, le
choix des ressources, la leçon du Rédacteur et le contrôle du Vérificateur.

Une leçon tient la structure et la longueur de la spec (1 500 mots, `lesson_markdown`) : son titre
est celui du module, ses liens et ses marqueurs `[1]`, `[2]` sont les deux premières sources du
prompt (jamais une adresse inventée)."""

import json
import re
from collections.abc import Callable, Sequence

from langchain_core.messages import BaseMessage

from app.agents.tools.plan_schema import (
    EdgeDraft,
    ModuleDraft,
    PlanDraft,
    SkillDraft,
    TaskDraft,
    WeekDraft,
)
from app.db.models.program import TaskType
from tests.e2e.scripted_models import Reply
from tests.support.lessons import lesson_markdown

LESSON_WORDS = 1500
RESOURCES_PICKED = 4
_TITLE = re.compile(r"^# (.+)$", re.MULTILINE)
_ADDRESS = re.compile(r"Adresse : (\S+)")
_SOURCE_ID = re.compile(r"source_id : (\S+) \(note")

type Writer = Callable[[Sequence[BaseMessage]], str]


def prompt_of(messages: Sequence[BaseMessage]) -> str:
    return "\n".join(str(m.content) for m in messages)


def expect(marker: str, reply: Reply) -> Callable[[Sequence[BaseMessage]], str]:
    """`reply`, à condition que l'appel soit bien celui attendu (`marker` dans le prompt) : un
    script décalé échoue tout de suite, en nommant l'étape, au lieu de répondre de travers."""

    def answer(messages: Sequence[BaseMessage]) -> str:
        if marker not in prompt_of(messages):
            raise RuntimeError(f"Réponse scriptée hors d'ordre : attendu « {marker} ».")
        return reply if isinstance(reply, str) else reply(messages)

    return answer


def _task(title: str, kind: TaskType, minutes: int, done: str) -> TaskDraft:
    return TaskDraft(title=title, type=kind, minutes=minutes, done_criterion=done)


def _week(theme: str, module: str, skill: str, tasks: list[TaskDraft]) -> WeekDraft:
    return WeekDraft(
        theme=theme,
        objective=f"Savoir mettre en œuvre : {skill}.",
        deliverable=f"Un dépôt qui montre : {skill}.",
        modules=[ModuleDraft(title=module, skills=[skill], tasks=tasks)],
    )


def program_plan() -> str:
    """Deux semaines d'un module, chacune avec sa pratique et finie par un quiz (~3 h par
    semaine : loin des 85 % du budget par défaut)."""
    first = _week(
        "Appeler un modèle de langage",
        "Appeler une API de LLM",
        "API de LLM",
        [
            _task("Lire la documentation de l'API", "lire", 60, "Notes prises sur l'API"),
            _task("Regarder une démonstration d'appel", "regarder", 30, "Démo comprise"),
            _task("Coder un premier appel", "pratiquer", 60, "Script qui répond"),
            _task("Faire le quiz de la semaine", "quiz", 20, "Quiz réussi"),
        ],
    )
    second = _week(
        "Évaluer un assistant",
        "Évaluer les réponses d'un LLM",
        "Évaluation de LLM",
        [
            _task("Lire un guide d'évaluation", "lire", 45, "Critères notés"),
            _task("Construire un jeu de tests", "pratiquer", 90, "Vingt cas écrits"),
            _task("Faire le quiz de la semaine", "quiz", 20, "Quiz réussi"),
        ],
    )
    plan = PlanDraft(
        title="Parcours AI product engineer",
        weeks=[first, second],
        skills=[
            SkillDraft(name="API de LLM", domain="IA générative"),
            SkillDraft(name="Évaluation de LLM", domain="IA générative"),
        ],
        edges=[EdgeDraft(before="API de LLM", after="Évaluation de LLM")],
    )
    return plan.model_dump_json()


def pick_resources(messages: Sequence[BaseMessage]) -> str:
    """Les 4 premières sources candidates du prompt (identifiants créés par la base)."""
    ids = _SOURCE_ID.findall(prompt_of(messages))[:RESOURCES_PICKED]
    kinds = ["documentation", "article", "cours", "depot"]
    picks = [
        {
            "source_id": sid,
            "type": kind,
            "duration_minutes": 30,
            "level": "debutant",
            "reason": "Explique clairement le sujet du module.",
        }
        for sid, kind in zip(ids, kinds, strict=False)
    ]
    return json.dumps({"resources": picks})


def write_lesson(messages: Sequence[BaseMessage]) -> str:
    """Leçon au titre du module, liée aux deux premières sources du prompt."""
    prompt = prompt_of(messages)
    structure = prompt[prompt.index("Structure EXACTE") :]
    title = _TITLE.search(structure)
    urls = _ADDRESS.findall(prompt)
    if title is None or len(urls) < 2:
        raise RuntimeError("Réponse scriptée : titre ou sources absents du prompt du Rédacteur.")
    return lesson_markdown(LESSON_WORDS, title=title.group(1).strip(), urls=(urls[0], urls[1]))


NO_CLAIM = json.dumps({"unsupported": []})
