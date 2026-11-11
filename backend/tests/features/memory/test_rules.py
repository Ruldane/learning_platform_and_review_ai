"""Règles d'écriture de la mémoire (D65) : qui écrit quoi, à quel niveau, avec quelle raison."""

import pytest

from app.core.errors import AppError
from app.features.memory.service.rules import resolve_write
from tests.features.memory.helpers import draft


def _code(**fields: object) -> str:
    with pytest.raises(AppError) as raised:
        resolve_write(draft(**fields))
    assert raised.value.status_code == 422
    return raised.value.code


def test_agent_cannot_write_documents() -> None:
    assert _code(kind="document", author="archivist") == "memory_kind_forbidden"


def test_agent_acquis_level_limited() -> None:
    assert _code(kind="acquis", author="archivist", level="valide") == "memory_level_forbidden"
    assert _code(kind="acquis", author="archivist", level="prouve") == "memory_level_forbidden"
    status, meta = resolve_write(draft(kind="acquis", author="archivist", level=None))
    assert status == "active" and meta["level"] == "declare"
    in_progress = resolve_write(draft(kind="acquis", author="archivist", level="en_cours"))
    assert in_progress[1]["level"] == "en_cours"


def test_agent_decision_goes_pending() -> None:
    assert resolve_write(draft(kind="decision", author="archivist"))[0] == "pending"
    assert resolve_write(draft(kind="lecon", author="writer"))[0] == "active"
    assert resolve_write(draft(kind="source", author="scout"))[0] == "active"


@pytest.mark.parametrize("reason", [None, "", "   \n"])
def test_agent_write_requires_reason(reason: str | None) -> None:
    assert _code(author="writer", reason=reason) == "memory_reason_required"


def test_user_writes_are_active_without_reason() -> None:
    status, meta = resolve_write(draft(kind="decision", author="user", reason=None))
    assert (status, meta) == ("active", {})
    declared = resolve_write(draft(kind="acquis", author="user", reason=None))
    assert declared[1] == {"level": "declare"}
    in_progress = resolve_write(draft(kind="acquis", author="user", level="en_cours"))
    assert in_progress[1]["level"] == "en_cours"
    assert resolve_write(draft(kind="document", author="user", reason=None))[0] == "active"


def test_user_cannot_set_a_level_above_en_cours() -> None:
    assert _code(kind="acquis", author="user", level="valide") == "memory_level_forbidden"


def test_a_level_only_concerns_an_acquis() -> None:
    assert _code(kind="lecon", author="user", level="declare") == "memory_level_forbidden"
    assert _code(kind="lecon", author="writer", level="declare") == "memory_level_forbidden"


def test_meta_keeps_evidence_and_reason_and_omits_the_rest() -> None:
    _, meta = resolve_write(
        draft(kind="lecon", author="writer", reason=" Leçon 1 publiée. ", evidence=("e1", "e2"))
    )
    assert meta == {"evidence": ["e1", "e2"], "reason": "Leçon 1 publiée."}
    assert resolve_write(draft(kind="lecon", author="user", reason=None))[1] == {}
