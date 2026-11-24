"""L'Assistant de suivi (SPEC 9.1, F5, D141) : parcours `application_intake`.

START -> load -> parse -> alerts -> ask <-> (réponse invalide) ; ask -> save -> announce -> END ;
ask -> leave -> END (`cancel`, `open`).

`load` lit le jour de January (son fuseau) par le port. `parse` donne la phrase à l'Assistant de
suivi (rapide, encadrée par `untrusted`) avec la date du jour et les jours de la semaine, pour que
« hier » ou « lundi dernier » se résolvent ; la sortie structurée est vérifiée par le code : une
date dans le futur, une entreprise ou un poste qui ne figurent pas dans la phrase sont renvoyés au
modèle (`structured_call`, deux nouveaux essais) ; une entreprise ou un poste restés vides
arrêtent le parcours (`intake_incomplete`) : rien n'est inventé. `alerts` cherche les doublons
(lecture). La confirmation est dans `confirm.py`. `save` crée la fiche par le port, idempotent par
session (SPEC 9.4) ; le seul nœud qui écrit.

Journaux : identifiants et nombres seulement, jamais la phrase ni un champ de la fiche (17.2)."""

import logging
import re
import unicodedata
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import Field, field_validator

from app.agents.nodes.tracker.confirm import DISTINCT, OPEN
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.application_intake import ApplicationIntakeState
from app.agents.tools.applications_port import COMPANY_MAX, TITLE_MAX, IntakeDraft
from app.core.clock import WEEKDAYS, english_day
from app.core.errors import AppError

AGENT = "tracker"
INTAKE_REQUEST = "Read January's sentence and return the application it describes."
INCOMPLETE = "Your sentence is missing the company or the role."
UNREADABLE = "Try again with the company, the role, and the date you applied."
NOTHING_CREATED = "No application was created."
PARSE_TIMEOUT_S = 300  # trois demandes au plus, chacune avec ses nouveaux essais (GLM)
CALENDAR_DAYS = 14
_WEEKDAYS = tuple(name.capitalize() for name in WEEKDAYS)
_RELATIVE = {0: "today", 1: "yesterday", 2: "the day before yesterday"}

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: ApplicationIntakeState) -> ApplicationIntakeState: ...


def day_label(day: date) -> str:
    """Give the weekday, English date, and unambiguous ISO date."""
    return f"{_WEEKDAYS[day.weekday()]} {english_day(day)} ({day.isoformat()})"


def calendar_lines(today: date) -> list[str]:
    """List the last `CALENDAR_DAYS` days, starting with today's date."""
    lines = []
    for back in range(CALENDAR_DAYS):
        label = day_label(today - timedelta(days=back))
        lines.append(f"{_RELATIVE[back]}: {label}" if back in _RELATIVE else label)
    return lines


def _plain(text: str) -> str:
    """Le texte sans accents ni casse (NFKD, combinants retirés, `casefold`), blancs réduits."""
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(bare.casefold().split())


def _words(text: str) -> set[str]:
    """Les mots d'un texte (lettres de tout alphabet, chiffres), sans accents ni casse :
    « L'Oréal » donne `l` et `oreal` ; un mot d'une lettre compte."""
    return set(re.findall(r"\w+", _plain(text)))


def _written(value: str, sentence: str) -> bool:
    """Le champ est fait de mots de la phrase ; sans aucun mot (ponctuation seule), il doit y
    figurer tel quel."""
    words = _words(value)
    return words <= _words(sentence) if words else _plain(value) in _plain(sentence)


class IntakeReading(IntakeDraft):
    """La lecture de la phrase : `company` et `title` vides si la phrase ne les dit pas (jamais
    inventés) ; le parcours s'arrête alors (`INCOMPLETE`)."""

    company: str = Field(default="", max_length=COMPANY_MAX)
    title: str = Field(default="", max_length=TITLE_MAX)


def reading_schema(today: date, text: str) -> type[IntakeReading]:
    """`IntakeReading` vérifié contre le jour de January et la phrase : une réponse refusée est
    renvoyée au modèle avec le motif (sans valeur recopiée) par `structured_call`."""

    class Reading(IntakeReading):
        @field_validator("applied_on")
        @classmethod
        def _not_future(cls, value: date | None) -> date | None:
            if value is not None and value > today:
                raise ValueError(
                    f"The application date is in the future. Today is {today.isoformat()}. "
                    "Use that date to resolve relative dates such as yesterday or last Monday."
                )
            return value

        @field_validator("company", "title", "contact_name")
        @classmethod
        def _from_the_sentence(cls, value: str | None) -> str | None:
            if value and not _written(value, text):
                raise ValueError(
                    "This field must be copied from the sentence. "
                    "Leave it blank if the sentence doesn't provide it."
                )
            return value

    return Reading


def parse_vars(text: str, today: date, language: str) -> dict[str, object]:
    return {
        "mode": "intake",
        "phrase": untrusted(text, "application sentence"),
        "today_line": day_label(today),
        "calendar": calendar_lines(today),
        "language": language,
    }


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: ApplicationIntakeState) -> ApplicationIntakeState:
        context = await deps.ports.applications.intake_context(deps.user_id)
        logger.info("Jour de January lu : session %s", deps.session_id)
        return {"today": context.today.isoformat(), "language": context.language}

    return load


async def _read(deps: GraphDeps, state: ApplicationIntakeState) -> IntakeReading:
    today = date.fromisoformat(state["today"])
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, **parse_vars(state["text"], today, state["language"]))
    try:
        return await structured_call(
            model,
            reading_schema(today, state["text"]),
            [SystemMessage(prompt), HumanMessage(INTAKE_REQUEST)],
            agent=AGENT,
            step="lecture",
            intent="reading your sentence",
        )
    except AppError as exc:
        if exc.code != "structured_output_invalid":
            raise
        raise AppError("intake_unreadable", UNREADABLE, 422) from None


def make_parse(deps: GraphDeps) -> Node:
    @node_timeout(PARSE_TIMEOUT_S)
    async def parse(state: ApplicationIntakeState) -> ApplicationIntakeState:
        """La fiche décrite par la phrase ; rejoué, il redemande sans rien écrire."""
        reading = await _read(deps, state)
        if not reading.company or not reading.title:
            logger.info("Phrase sans entreprise ou sans poste : session %s", deps.session_id)
            raise AppError("intake_incomplete", INCOMPLETE, 422)
        draft = IntakeDraft.model_validate(reading.model_dump())
        logger.info("Phrase lue : session %s, statut %s", deps.session_id, draft.status)
        return {"draft": draft.model_dump(mode="json")}

    return parse


def make_alerts(deps: GraphDeps) -> Node:
    @node_timeout()
    async def alerts(state: ApplicationIntakeState) -> ApplicationIntakeState:
        """Les fiches qui ressemblent (lecture, mêmes règles que la route)."""
        draft = IntakeDraft.model_validate(state["draft"])
        found = await deps.ports.applications.intake_alerts(deps.user_id, draft)
        logger.info("Doublons cherchés : session %s, %d alerte(s)", deps.session_id, len(found))
        return {"alerts": [asdict(alert) for alert in found]}

    return alerts


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: ApplicationIntakeState) -> ApplicationIntakeState:
        """La création, la seule écriture : « autre poste » couvre les fiches de l'alerte."""
        answer = state["answer"]
        assert answer is not None  # garanti par `route_confirm`
        distinct = (
            [a["application_id"] for a in state["alerts"]] if answer["choice"] == DISTINCT else []
        )
        draft = IntakeDraft.model_validate(answer["draft"])
        info = await deps.ports.applications.intake_info(deps.user_id, draft)
        application_id = await deps.ports.applications.save_intake(
            deps.user_id, deps.session_id, draft, distinct
        )
        logger.info(
            "Fiche créée : session %s, fiche %s, %d information(s)",
            deps.session_id,
            application_id,
            len(info),
        )
        return {"application_id": application_id, "info": [asdict(item) for item in info]}

    return save


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


def _artifact(application_id: str, title: str, info: list[dict[str, Any]] | None = None) -> None:
    artifact: dict[str, Any] = {
        "artifact_id": application_id,
        "kind": "application",
        "title": title,
        "url": f"/applications/{application_id}",
    }
    if info:
        artifact["info"] = info  # « même entreprise depuis 30 jours » (SPEC 6.3), pour l'écran
    emit("artifact.ready", artifact, agent=AGENT)


def announce(state: ApplicationIntakeState) -> ApplicationIntakeState:
    """La fiche créée, à ouvrir, avec les simples informations « même entreprise » (M4)."""
    assert state["answer"] is not None  # garanti par `route_confirm`
    draft = state["answer"]["draft"]
    info = state.get("info", [])
    text = " ".join(
        [
            f"Application created for {draft['title']} at {draft['company']}.",
            *(i["message"] for i in info),
        ]
    )
    _say("fin", text)
    _artifact(state["application_id"], f"Application at {draft['company']}", info)
    return {"summary": text}


def leave(state: ApplicationIntakeState) -> ApplicationIntakeState:
    """Annulation, ou ouverture de la fiche existante (la plus forte alerte) : rien n'est créé."""
    assert state["answer"] is not None  # garanti par `route_confirm`
    if state["answer"]["choice"] == OPEN:
        application_id = state["alerts"][0]["application_id"]
        _say("fin", "Here is the existing application.")
        _artifact(application_id, "Existing application")
        return {"application_id": application_id, "summary": "Opened the existing application."}
    _say("fin", NOTHING_CREATED)
    return {"summary": NOTHING_CREATED}
