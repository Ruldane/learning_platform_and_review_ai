"""État du parcours `capture` (D108) : la source capturée, ce que l'Archiviste en a lu, l'instantané
des liens vers le programme (références `m3`, `t12` et leurs ids, F7), le résumé, ce qui est rangé
et les réponses de January."""

from typing import Any, TypedDict


class CaptureState(TypedDict, total=False):
    url: str | None
    text: str | None
    document_id: str | None
    source: str  # `url`, `text` ou `document` (la source d'origine)
    pasted: bool  # le texte vient de la question posée après un lien illisible
    unreadable: bool  # le lien n'a pas pu être lu : la question du texte suit
    material: dict[str, Any]  # `CaptureMaterial` en JSON
    links: dict[str, Any]  # `ProgramLinks` en JSON (dates ISO) : l'instantané des références
    digest: dict[str, Any]  # `CaptureDigest` en JSON, références inconnues retirées
    stored: dict[str, Any]  # `CaptureStored` en JSON
    tick: bool  # January a dit oui à la tâche couverte
    ticked: bool  # la tâche est cochée
    want_cards: bool  # January a dit oui aux fiches
    cards_created: int
    outcome: str  # `cancelled` : capture abandonnée ; sinon vide
    summary: str
