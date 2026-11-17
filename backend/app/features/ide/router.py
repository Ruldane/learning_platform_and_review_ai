"""API de l'IDE Python (phase 10, P1) : exercices, séances, exécutions, professeur, notes,
préférences et consommation. Surface posée par 10.P ; 10.A2 remplit les exercices, les séances, les
exécutions et les notes ; 10.A3 remplit `exercises/generate`, `teach` (barrière de coût du
professeur), `preferences` et `usage`. Au nom de l'utilisatrice courante (404 sur l'objet
d'une autre) ; `accept`, `reject` et `PUT preferences` sont des gestes de l'interface (exclus du
MCP) ; `PUT files` est aussi celui de Claude, sous l'interrupteur de January (10.X)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Response
from starlette.requests import HTTPConnection

from app.core.caller import CallerDep
from app.core.deps import CurrentUserDep, Db, get_current_user
from app.core.field_paths import FieldPathsRoute
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
from app.features.ide.service import IdeService
from app.features.ide.service.errors import mcp_prefs_forbidden
from app.features.ide.service.teaching import TeachingService
from app.features.ide.service.usage import UsageService

router = APIRouter(
    prefix="/ide",
    tags=["ide"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(get_current_user)],
)

Id = Annotated[str, Path(min_length=1, max_length=36)]


def get_ide_service(
    conn: HTTPConnection, current: CurrentUserDep, db: Db, caller: CallerDep
) -> IdeService:
    """Le service de l'utilisatrice courante, avec le bac à sable posé par la composition."""
    return IdeService(db, current.id, conn.app.state.providers.sandbox, caller)


def teaching_service(conn: HTTPConnection, current: CurrentUserDep, db: Db) -> TeachingService:
    """La barrière de coût du professeur ; le lanceur de sessions est celui de l'application."""
    return TeachingService(db, current.id, conn.app.state.launcher)


def usage_service(current: CurrentUserDep, db: Db) -> UsageService:
    return UsageService(db, current.id)


Ide = Annotated[IdeService, Depends(get_ide_service)]
Teaching = Annotated[TeachingService, Depends(teaching_service)]
Usage = Annotated[UsageService, Depends(usage_service)]
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Introuvable (ou pas à moi)."}}
_RUN_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`session_not_found`"},
    409: {"description": "`run_in_progress` : une exécution est déjà en cours"},
    422: {"description": "`entry_missing`, `run_refused`"},
    503: {"description": "`sandbox_unavailable` : le bac à sable est arrêté"},
}
_NOTE_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`session_not_found`"},
    409: {"description": "`note_stale` : le fichier a changé depuis la lecture"},
    422: {"description": "`note_invalid` : plage, fichier ou empreinte (`details.file_hash`)"},
}
_ACCEPT_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`note_not_found`"},
    409: {"description": "`note_stale` (la note passe à `stale`), `note_closed`, `not_a_proposal`"},
}


@router.get("/exercises", response_model=list[ExerciseOut])
async def list_exercises(ide: Ide) -> list[ExerciseOut]:
    """Mes exercices, les plus récents d'abord."""
    return await ide.list_exercises()


@router.post("/exercises", response_model=ExerciseOut, status_code=201)
async def create_exercise(body: ExerciseIn, ide: Ide) -> ExerciseOut:
    """Ajoute un exercice écrit à la main (ou par Claude : `origin` vient de l'appelant)."""
    return await ide.create_exercise(body)


@router.post("/exercises/generate", response_model=IdeSessionStarted, status_code=202)
async def generate_exercise(body: ExerciseGenerateIn, teaching: Teaching) -> IdeSessionStarted:
    """Fait générer un exercice par les agents : rend aussitôt la session à suivre. L'exercice
    n'est rangé qu'une fois sa solution vérifiée dans le bac à sable."""
    return await teaching.generate(body)


@router.delete(
    "/exercises/{exercise_id}", status_code=204, response_class=Response, responses=_NOT_FOUND
)
async def delete_exercise(exercise_id: Id, ide: Ide) -> Response:
    """Supprime un exercice (ses séances restent). 404 si ce n'est pas le mien."""
    await ide.delete_exercise(exercise_id)
    return Response(status_code=204)


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(ide: Ide) -> list[SessionSummary]:
    """Mes séances de code, la plus récente d'abord."""
    return await ide.list_sessions()


@router.post("/sessions", response_model=IdeSessionOut, status_code=201, responses=_NOT_FOUND)
async def create_session(body: SessionCreateIn, ide: Ide) -> IdeSessionOut:
    """Ouvre une séance sur un exercice, ou une séance libre."""
    return await ide.open_session(body.exercise_id, body.title)


@router.get("/sessions/{session_id}", response_model=IdeSessionOut, responses=_NOT_FOUND)
async def get_session(session_id: Id, ide: Ide) -> IdeSessionOut:
    """Une séance avec ses fichiers."""
    return await ide.get_session(session_id)


@router.put(
    "/sessions/{session_id}/files",
    response_model=IdeSessionOut,
    responses={
        403: {"description": "`mcp_ide_write_off` : Claude n'y est pas autorisé (interrupteur)"},
        404: {"description": "`session_not_found`"},
        409: {"description": "`stale_base` : le fichier a changé depuis la lecture (Claude)"},
        422: {
            "description": "`entry_missing`, `entry_invalid`, `files_too_large`, "
            "`base_hash_required`, `mcp_write_one_file`"
        },
    },
)
async def put_files(session_id: Id, body: FilesPutIn, ide: Ide) -> IdeSessionOut:
    """Enregistre les fichiers de la séance (20 au plus, 200 Ko) : l'interface les remplace tous ;
    Claude (MCP, interrupteur allumé) écrit un fichier avec `base_hash`."""
    return await ide.save_files(session_id, body.files, body.entry, body.base_hash)


@router.get("/sessions/{session_id}/runs", response_model=list[RunOut], responses=_NOT_FOUND)
async def list_runs(session_id: Id, ide: Ide) -> list[RunOut]:
    """Les 20 dernières exécutions de la séance, la plus récente d'abord (lues toutes les 3 s par la
    page ouverte : une exécution lancée par Claude y apparaît)."""
    return await ide.list_runs(session_id)


@router.post(
    "/sessions/{session_id}/runs", response_model=RunOut, status_code=202, responses=_RUN_ERRORS
)
async def start_run(session_id: Id, body: RunIn, ide: Ide) -> RunOut:
    """Dépose une exécution ou une vérification dans le bac à sable (une par utilisatrice)."""
    return await ide.start_run(session_id, body.kind, body.entry)


@router.get(
    "/runs/{run_id}",
    response_model=RunProgress,
    responses={
        404: {"description": "`run_not_found`"},
        503: {"description": "`sandbox_unavailable`"},
    },
)
async def read_run(run_id: Id, ide: Ide, after: Annotated[int, Query(ge=0)] = 0) -> RunProgress:
    """La sortie de l'exécution à partir de l'octet `after` (interrogation toutes les 300 ms)."""
    return await ide.get_run(run_id, after)


@router.post(
    "/sessions/{session_id}/teach",
    response_model=TeachOut,
    status_code=202,
    responses={
        404: {"description": "`session_not_found`, `run_not_found`"},
        422: {"description": "Déclencheur inconnu, ou question vide"},
    },
)
async def teach(session_id: Id, body: TeachIn, teaching: Teaching) -> TeachOut:
    """Réveille le professeur : un graphe (`session_id`), un renvoi à la note précédente
    (`reference_note_id`) ou rien (`skipped`). Seule route qui lance le professeur : ni la
    sauvegarde des fichiers ni la frappe ne l'appellent."""
    return await teaching.teach(session_id, body)


@router.get("/sessions/{session_id}/notes", response_model=list[NoteOut], responses=_NOT_FOUND)
async def list_notes(session_id: Id, ide: Ide) -> list[NoteOut]:
    """Les notes de la séance : indices, explications, annotations, propositions, renvois."""
    return await ide.list_notes(session_id)


@router.post(
    "/sessions/{session_id}/notes",
    response_model=NoteOut,
    status_code=201,
    responses=_NOTE_ERRORS,
)
async def add_note(session_id: Id, body: NoteIn, ide: Ide) -> NoteOut:
    """Ajoute une note ; l'auteur est celui de l'appelant (moi, le professeur, Claude)."""
    return await ide.add_note(session_id, body)


@router.post("/notes/{note_id}/accept", response_model=IdeSessionOut, responses=_ACCEPT_ERRORS)
async def accept_note(note_id: Id, ide: Ide) -> IdeSessionOut:
    """Applique une proposition au fichier si celui-ci n'a pas changé (sinon 409 `note_stale`).
    Geste de l'interface, jamais du MCP."""
    return await ide.accept_note(note_id)


@router.post("/notes/{note_id}/reject", response_model=NoteOut, responses=_ACCEPT_ERRORS)
async def reject_note(note_id: Id, ide: Ide) -> NoteOut:
    """Refuse une proposition. Geste de l'interface, jamais du MCP."""
    return await ide.reject_note(note_id)


@router.get("/preferences", response_model=PreferencesOut)
async def get_preferences(usage: Usage) -> PreferencesOut:
    """Mode et style du professeur, minuterie d'inactivité, plafonds de jetons."""
    return await usage.preferences()


@router.put(
    "/preferences",
    response_model=PreferencesOut,
    responses={403: {"description": "`mcp_prefs_forbidden` : jamais par le MCP"}},
)
async def put_preferences(body: PreferencesIn, usage: Usage, caller: CallerDep) -> PreferencesOut:
    """Remplace les préférences (professeur, interrupteur d'écriture de Claude). Geste de
    l'interface : jamais du MCP, qui n'a pas à régler son propre budget ni ses propres droits."""
    if caller.kind == "mcp":
        raise mcp_prefs_forbidden()
    return await usage.save_preferences(body)


@router.get("/usage", response_model=UsageOut, responses=_NOT_FOUND)
async def get_usage(
    usage: Usage, session_id: Annotated[str | None, Query(max_length=36)] = None
) -> UsageOut:
    """Les jetons du professeur : séance (si `session_id`), jour, plafonds, mode sur demande."""
    return await usage.usage(session_id)
