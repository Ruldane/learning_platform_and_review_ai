"""Schémas du profil maître (SPEC 5.1, 14.2 ; D124). Une 422 ne recopie jamais la saisie : sur les
routes du profil, `details.fields` nomme les champs par leur chemin (« experiences.2.role »)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.agents.tools.cv_schema import MasterProfileData
from app.db.models.career import ProfileOrigin, ProfileStatus


class ProfileOut(BaseModel):
    """Une version du profil. `source` : `archivist` (brouillon tiré des documents) ou `january`
    (version qu'elle a validée). `dropped` : lignes retirées du brouillon (chiffre ou fait
    introuvable dans les documents, texte invisible), montrées à January seule."""

    version: int
    status: ProfileStatus
    data: MasterProfileData
    source: ProfileOrigin
    created_at: datetime
    dropped: list[str]


class ProfileStateOut(BaseModel):
    """`draft` : seulement s'il est plus récent que la version validée. `session_id` : capture
    du profil en cours (à suivre par ses événements), sinon `None`. `source_document_id` : le CV
    (PDF étiqueté `cv`) du dernier import du profil, s'il est encore dans la mémoire, sinon
    `None` (« Utiliser le CV de mon profil » pour capturer un gabarit)."""

    validated: ProfileOut | None
    draft: ProfileOut | None
    session_id: str | None
    source_document_id: str | None


class ProfilePutIn(BaseModel):
    """`base_version` : la version que January a relue (la dernière, sinon 409
    `profile_conflict`) ; `None` s'il n'existe encore aucune version."""

    data: MasterProfileData
    base_version: int | None = Field(default=None, ge=1)


class ProfileVersionOut(BaseModel):
    version: int
    status: ProfileStatus
    source: ProfileOrigin
    created_at: datetime


class ProfileImportStarted(BaseModel):
    """Capture du profil lancée : la session `cv_capture` et les documents rangés dans la mémoire
    (CV d'abord, puis LinkedIn)."""

    session_id: str
    document_ids: list[str]
