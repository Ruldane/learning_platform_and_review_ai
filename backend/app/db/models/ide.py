"""Tables de l'IDE Python (phase 10, P3) : exercices, séances de code, exécutions, notes du
professeur ou de Claude, préférences. Aucune clé étrangère (comme le quotidien) : une séance
survit à la suppression de son exercice."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents` (le professeur est un graphe), qui ne peut pas importer une
# feature (contrat 6).
ExerciseOrigin = Literal["user", "generated", "claude"]
RunKind = Literal["run", "check"]
RunStatus = Literal["running", "done", "timeout", "killed", "error"]
NoteKind = Literal["hint", "explanation", "annotation", "proposal", "reference"]
NoteAuthor = Literal["professor", "claude", "user"]
NoteStatus = Literal["open", "accepted", "rejected", "stale"]
TeacherMode = Literal["auto", "on_demand"]
# `guide` : le professeur donne des indices gradués ; `pair` : binôme (annotations en marge et
# propositions à accepter).
TeacherStyle = Literal["guide", "pair"]
# D'où vient le geste (`app/core/caller.py`) : l'interface ou Claude par le MCP.
Origin = Literal["app", "mcp"]


class IdeExercise(UserScopedMixin, Base):
    """Un exercice : l'énoncé et les fichiers de départ (chemin -> contenu). `origin` : écrit par
    January, généré par le graphe, ou ajouté par Claude."""

    __tablename__ = "ide_exercises"

    title: Mapped[str] = mapped_column(String(120))
    statement: Mapped[str] = mapped_column(Text)
    files: Mapped[dict[str, Any]] = mapped_column(default=dict)
    entry: Mapped[str] = mapped_column(String(200), default="main.py")
    origin: Mapped[str] = mapped_column(String(16), default="user")
    topic: Mapped[str | None] = mapped_column(String(300), default=None)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)


class IdeSession(UserScopedMixin, Base):
    """Une séance de code : les fichiers en cours (au plus 20, 200 Ko). `exercise_id` est vide
    pour une séance libre. `passed_at` : posé à la première vérification (`check`) réussie."""

    __tablename__ = "ide_sessions"
    __table_args__ = (Index("ix_ide_sessions_user_updated", "user_id", "updated_at"),)

    exercise_id: Mapped[str | None] = mapped_column(String(36), default=None)
    title: Mapped[str] = mapped_column(String(120))
    files: Mapped[dict[str, Any]] = mapped_column(default=dict)
    entry: Mapped[str] = mapped_column(String(200), default="main.py")
    # Jetons du professeur (entrée + sortie) consommés dans cette séance : plafond de séance.
    teacher_tokens: Mapped[int] = mapped_column(Integer, default=0)
    # Compteur d'écritures de fichiers : la base compare « lu = actuel » (10.X).
    files_version: Mapped[int] = mapped_column(Integer, default=0)
    passed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)

    @property
    def passed(self) -> bool:
        return self.passed_at is not None


class IdeRun(UserScopedMixin, Base):
    """Une exécution (ou une vérification). `output` : la sortie lue au bac, 64 Kio au plus ;
    `status` reste `running` tant que le bac n'a pas rendu son résultat ; `error_signature` :
    signature de l'erreur (40 signes au plus, interne : jamais dans les schémas de sortie)."""

    __tablename__ = "ide_runs"
    __table_args__ = (Index("ix_ide_runs_session", "session_id", "created_at"),)

    session_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(8), default="run")
    entry: Mapped[str] = mapped_column(String(200), default="main.py")
    status: Mapped[str] = mapped_column(String(16), default="running")
    exit_code: Mapped[int | None] = mapped_column(Integer, default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    output: Mapped[str] = mapped_column(Text, default="")
    requested_by: Mapped[str] = mapped_column(String(60), default="app")
    # `app` (l'interface) ou `mcp` (Claude) : la page affiche « lancée par Claude » (10.X).
    origin: Mapped[str] = mapped_column(String(8), default="app")
    error_signature: Mapped[str | None] = mapped_column(String(40), default=None)


class IdeNote(UserScopedMixin, Base):
    """Une note de séance (P8) : indice, explication, annotation en marge, proposition de
    correction ou renvoi à une note précédente (`reference_note_id`). Le professeur interne et
    Claude écrivent par le même service ; seul `author` change. `base_hash` : sha256 hexadécimal
    du contenu du fichier (UTF-8) au moment d'une proposition ; `replacement` : le texte qui
    remplace les lignes `line_start` à `line_end` (P9)."""

    __tablename__ = "ide_notes"
    __table_args__ = (Index("ix_ide_notes_session", "session_id", "created_at"),)

    session_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(16))
    author: Mapped[str] = mapped_column(String(16))
    author_label: Mapped[str | None] = mapped_column(String(60), default=None)
    # `app` ou `mcp` : d'où vient le geste (le professeur interne et January sont `app`).
    origin: Mapped[str] = mapped_column(String(8), default="app")
    status: Mapped[str] = mapped_column(String(16), default="open")
    file_path: Mapped[str | None] = mapped_column(String(200), default=None)
    line_start: Mapped[int | None] = mapped_column(Integer, default=None)
    line_end: Mapped[int | None] = mapped_column(Integer, default=None)
    content: Mapped[str] = mapped_column(Text)
    replacement: Mapped[str | None] = mapped_column(Text, default=None)
    base_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    reference_note_id: Mapped[str | None] = mapped_column(String(36), default=None)
    # Empreinte de l'erreur et de son lieu : une même erreur au même endroit ne se réexplique pas.
    error_key: Mapped[str | None] = mapped_column(String(64), default=None)
    # Niveau réel d'un indice gradué (1 à 3), vide pour les autres notes.
    level: Mapped[int | None] = mapped_column(Integer, default=None)


class IdePreference(UserScopedMixin, Base):
    """Les préférences du professeur, une ligne par compte : mode (`auto` ou `on_demand`),
    minuterie d'inactivité (30 s, en option) et plafonds de jetons (séance, jour)."""

    __tablename__ = "ide_preferences"
    # `uq_ide_preferences_user_id` : une ligne par compte.
    __table_args__ = (UniqueConstraint("user_id"),)

    teacher_mode: Mapped[str] = mapped_column(String(16), default="auto")
    teacher_style: Mapped[str] = mapped_column(String(8), default="guide")
    idle_trigger: Mapped[bool] = mapped_column(Boolean, default=False)
    # Interrupteur de January : Claude (MCP) peut écrire dans ses fichiers. Éteint par défaut ;
    # réglable seulement depuis l'interface.
    mcp_can_write_files: Mapped[bool] = mapped_column(Boolean, default=False)
    session_cap: Mapped[int] = mapped_column(Integer, default=100_000)
    day_cap: Mapped[int] = mapped_column(Integer, default=300_000)
