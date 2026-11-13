"""Étape « capture » du contrôle de fin de phase 5 : un lien lisible est rangé (élément de
mémoire, entrée de journal), un lien illisible est signalé tout de suite puis rangé avec le texte
collé (F18). Les questions de tâche et de fiches reçoivent « non » : le contrôle ne touche ni au
programme ni aux révisions. Rien de ce qui est envoyé ou reçu n'apparaît dans un message
d'échec ni dans la sortie : seulement des étapes, des nombres, des codes et des identifiants."""

from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase5_drive import drive
from scripts.phase5_rules import option_value
from scripts.phase5_steps import Etude

STEP = "capture"
READABLE_URL = "https://docs.python.org/3/tutorial/index.html"
UNREADABLE_URL = "https://example.invalid/"
PASTED_TEXT = (
    "Notes du contrôle de fin de phase : une liste en compréhension construit une liste à "
    "partir d'une boucle et d'un filtre, en une seule expression."
)
UNREADABLE_S = 30.0  # le lien illisible est signalé en moins de 30 secondes


def _no(question: dict[str, Any]) -> str:
    return option_value(question, "no", step=STEP)


def _paste(question: dict[str, Any]) -> dict[str, Any]:
    option_value(question, "cancel", step=STEP)  # « Abandonner » reste offert
    return {"answers": {"text": PASTED_TEXT}}


async def _entry_of(run: Run, session_id: str) -> dict[str, Any]:
    """L'entrée de journal de la capture, avec son élément de mémoire (lisible, sans le lire)."""
    page = await expect_ok(run, STEP, "GET", "/journal", params={"kind": "capture", "limit": 20})
    entry = next((e for e in page["entries"] if e["links"]["session_id"] == session_id), None)
    if entry is None:
        raise CheckFailed(STEP, f"Aucune entrée de journal pour la capture {session_id}.")
    item = entry["links"]["memory_item_id"]
    if not item:
        raise CheckFailed(STEP, f"Entrée {entry['id']} sans élément de mémoire.")
    await expect_ok(run, STEP, "GET", f"/memory/items/{item}")
    return dict(entry)


async def _start(run: Run, body: dict[str, str]) -> str:
    started = await expect_ok(run, STEP, "POST", "/capture", json=body)
    return str(started["session_id"])


async def capture_link(run: Run, st: Etude) -> None:
    session_id = await _start(run, {"url": READABLE_URL})
    asked = await drive(run, STEP, session_id, {"capture_task": _no, "capture_cards": _no})
    await _entry_of(run, session_id)
    st.captures.append(session_id)
    print(f"    lien lisible : rangé, {len(asked)} question(s) de suite", flush=True)


async def capture_unreadable(run: Run, st: Etude) -> None:
    session_id = await _start(run, {"url": UNREADABLE_URL})
    answers = {"capture_text": _paste, "capture_task": _no, "capture_cards": _no}
    asked = await drive(run, STEP, session_id, answers)
    if not asked or asked[0][0] != "capture_text":
        raise CheckFailed(STEP, f"Lien illisible sans question « capture_text » ({session_id}).")
    if asked[0][1] > UNREADABLE_S:
        raise CheckFailed(
            STEP, f"Lien illisible signalé après {asked[0][1]:.0f} s : {UNREADABLE_S:.0f} au plus."
        )
    await _entry_of(run, session_id)
    st.captures.append(session_id)
    print(f"    lien illisible : question en {asked[0][1]:.1f} s, texte collé rangé", flush=True)


async def check_capture(run: Run, st: Etude) -> None:
    await capture_link(run, st)
    await capture_unreadable(run, st)
