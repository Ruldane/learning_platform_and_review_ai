"""API de l'IDE Python (phase 10, P1) : exercices, séances, exécutions, professeur, notes,
préférences et consommation. Posée par 10.P (surface et schémas définitifs) : chaque route répond
501 `not_implemented` jusqu'à ce que 10.A2 (exercices, séances, notes, préférences), 10.A1
(exécutions) et 10.A3 (professeur, consommation) la remplissent. Au nom de l'utilisatrice
courante ; `accept`, `reject` et `PUT files` sont des gestes de l'interface (exclus du MCP)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.core.deps import get_current_user
from app.core.field_paths import FieldPathsRoute
from app.core.stubs import not_implemented
from app.features.ide.schemas import (
    ExerciseGenerateIn,
    ExerciseIn,
    ExerciseOut,
    FilesPutIn,
    IdeSessionOut,
    IdeSessionStarted,
    NoteIn,
    NoteOut,
    PreferencesIn,
    PreferencesOut,
    RunIn,
    RunOut,
    RunProgress,
    SessionCreateIn,
    SessionSummary,
    TeachIn,
    TeachOut,
    UsageOut,
)

router = APIRouter(
    prefix="/ide",
    tags=["ide"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(get_current_user)],
)

Id = Annotated[str, Path(min_length=1, max_length=36)]


@router.get("/exercises", response_model=list[ExerciseOut])
async def list_exercises() -> list[ExerciseOut]:
    """Mes exercices, les plus récents d'abord."""
    not_implemented()


@router.post("/exercises", response_model=ExerciseOut, status_code=201)
async def create_exercise(body: ExerciseIn) -> ExerciseOut:
    """Ajoute un exercice écrit à la main (ou par Claude : `origin` vient de l'appelant)."""
    not_implemented()


@router.post("/exercises/generate", response_model=IdeSessionStarted, status_code=202)
async def generate_exercise(body: ExerciseGenerateIn) -> IdeSessionStarted:
    """Fait générer un exercice par les agents : rend aussitôt la session à suivre."""
    not_implemented()


@router.delete("/exercises/{exercise_id}", status_code=204, response_class=Response)
async def delete_exercise(exercise_id: Id) -> Response:
    """Supprime un exercice (ses séances restent). 404 si ce n'est pas le mien."""
    not_implemented()


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    """Mes séances de code, la plus récente d'abord."""
    not_implemented()


@router.post("/sessions", response_model=IdeSessionOut, status_code=201)
async def create_session(body: SessionCreateIn) -> IdeSessionOut:
    """Ouvre une séance sur un exercice, ou une séance libre."""
    not_implemented()


@router.get("/sessions/{session_id}", response_model=IdeSessionOut)
async def get_session(session_id: Id) -> IdeSessionOut:
    """Une séance avec ses fichiers."""
    not_implemented()


@router.put("/sessions/{session_id}/files", response_model=IdeSessionOut)
async def put_files(session_id: Id, body: FilesPutIn) -> IdeSessionOut:
    """Remplace les fichiers de la séance (20 au plus, 200 Ko). Geste de l'interface."""
    not_implemented()


@router.post("/sessions/{session_id}/runs", response_model=RunOut, status_code=202)
async def start_run(session_id: Id, body: RunIn) -> RunOut:
    """Dépose une exécution ou une vérification dans le bac à sable (une par utilisatrice)."""
    not_implemented()


@router.get("/runs/{run_id}", response_model=RunProgress)
async def read_run(run_id: Id, after: Annotated[int, Query(ge=0)] = 0) -> RunProgress:
    """La sortie de l'exécution à partir de l'octet `after` (interrogation toutes les 300 ms)."""
    not_implemented()


@router.post("/sessions/{session_id}/teach", response_model=TeachOut, status_code=202)
async def teach(session_id: Id, body: TeachIn) -> TeachOut:
    """Réveille le professeur : un graphe (`session_id`), un renvoi à la note précédente
    (`reference_note_id`) ou rien (`skipped`)."""
    not_implemented()


@router.get("/sessions/{session_id}/notes", response_model=list[NoteOut])
async def list_notes(session_id: Id) -> list[NoteOut]:
    """Les notes de la séance : indices, explications, annotations, propositions, renvois."""
    not_implemented()


@router.post("/sessions/{session_id}/notes", response_model=NoteOut, status_code=201)
async def add_note(session_id: Id, body: NoteIn) -> NoteOut:
    """Ajoute une note ; l'auteur est celui de l'appelant (moi, le professeur, Claude)."""
    not_implemented()


@router.post("/notes/{note_id}/accept", response_model=IdeSessionOut)
async def accept_note(note_id: Id) -> IdeSessionOut:
    """Applique une proposition au fichier si celui-ci n'a pas changé (sinon 409 `note_stale`).
    Geste de l'interface, jamais du MCP."""
    not_implemented()


@router.post("/notes/{note_id}/reject", response_model=NoteOut)
async def reject_note(note_id: Id) -> NoteOut:
    """Refuse une proposition. Geste de l'interface, jamais du MCP."""
    not_implemented()


@router.get("/preferences", response_model=PreferencesOut)
async def get_preferences() -> PreferencesOut:
    """Mode du professeur, minuterie d'inactivité, plafonds de jetons."""
    not_implemented()


@router.put("/preferences", response_model=PreferencesOut)
async def put_preferences(body: PreferencesIn) -> PreferencesOut:
    """Remplace les préférences du professeur."""
    not_implemented()


@router.get("/usage", response_model=UsageOut)
async def get_usage(session_id: Annotated[str | None, Query(max_length=36)] = None) -> UsageOut:
    """Les jetons du professeur : séance (si `session_id`), jour, plafonds, mode sur demande."""
    not_implemented()
