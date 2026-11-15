"""Archive du kit (`GET /applications/{id}/kit.zip`, D143) : un fichier Markdown par pièce dans
l'ordre de F16, le PDF de la version prête, `LISEZMOI.txt` qui nomme les pièces à vérifier et les
pièces omises ; nom ASCII ; accès réservé à January."""

import io
import zipfile

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update

from app.agents.tools.kit_schema import KIT_KINDS
from app.db.models.career import CvVersion
from app.features.cv.service.naming import kit_filename
from tests.features.applications.conftest import API, add_posting, add_version
from tests.features.applications.kit_support import COMPANY, ready_application, save

PDF = b"%PDF-1.4 fictif"
NAMES = [f"{rank:02d}_{kind}.md" for rank, kind in enumerate(KIT_KINDS, 1)]

pytestmark = pytest.mark.usefixtures("client")


async def fetch(
    client: httpx.AsyncClient, application_id: str
) -> tuple[httpx.Response, zipfile.ZipFile]:
    r = await client.get(f"{API}/{application_id}/kit.zip")
    assert r.status_code == 200, r.text
    return r, zipfile.ZipFile(io.BytesIO(r.content))


def text(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8")


async def full_kit(app: FastAPI, application_id: str, **meta: dict[str, object]) -> None:
    for kind in KIT_KINDS:
        await save(app, application_id, kind, content=f"Contenu {kind}", meta=meta.get(kind))


async def ready_pdf(app: FastAPI, me: str, posting_id: str) -> str:
    """Une version de CV prête, son PDF rangé dans le stockage."""
    version_id = await add_version(app, posting_id)
    key = await app.state.career.cv.storage.save(me, "cv_versions", PDF, ".pdf")
    async with app.state.session_factory() as db:
        await db.execute(
            update(CvVersion)
            .where(CvVersion.id == version_id)
            .values(storage_key=key, filename="CV_Camille_Exemple_Societe_Fictive.pdf")
        )
        await db.commit()
    return version_id


async def test_zip_contains_pieces_and_pdf(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    posting = await add_posting(app, text="Texte de l'offre fictive.")
    version_id = await ready_pdf(app, me, posting)
    application_id = await ready_application(client, app, posting_id=posting)
    await full_kit(app, application_id, cv={"version_id": version_id})
    r, archive = await fetch(client, application_id)
    assert r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"] == (
        'attachment; filename="Kit_Societe_Fictive_Developpeuse_IA.zip"'
    )
    assert r.headers["cache-control"] == "no-store"
    assert archive.namelist() == [*NAMES, "CV_Camille_Exemple_Societe_Fictive.pdf", "LISEZMOI.txt"]
    assert archive.read("CV_Camille_Exemple_Societe_Fictive.pdf") == PDF
    assert text(archive, "02_letter.md") == "Contenu letter\n"
    assert archive.testzip() is None
    readme = text(archive, "LISEZMOI.txt")
    assert "Pièces à vérifier avant de les utiliser :\n- aucune" in readme
    assert "Pièces absentes de l'archive :\n- aucune" in readme
    assert "CV en PDF : CV_Camille_Exemple_Societe_Fictive.pdf" in readme


async def test_zip_names_to_check_pieces(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await ready_application(client, app)
    for kind in KIT_KINDS:
        await save(app, application_id, kind, content=f"Contenu {kind}")
    await save(
        app, application_id, "letter", session="s-2", status="to_check",
        content="Lettre à relire", meta={"flags": ["5", "Kubernetes"]},
    )  # fmt: skip
    await save(
        app, application_id, "form_answers", session="s-2", status="to_check",
        content="### Quelles sont vos prétentions salariales ?\nÀ remplir par toi",
    )  # fmt: skip
    _, archive = await fetch(client, application_id)
    readme = text(archive, "LISEZMOI.txt")
    assert (
        "- 02_letter.md (Lettre de motivation) : termes que ton profil ne dit pas : 5, Kubernetes"
        in readme
    )
    assert (
        "- 05_form_answers.md (Réponses aux questions du formulaire) : 1 réponse(s) salariale(s)"
        in readme
    )
    assert "01_cv.md (CV" not in readme and "07_pitch.md (Pitch" not in readme
    assert text(archive, "02_letter.md") == "Lettre à relire\n"  # la pièce à vérifier y figure


async def test_zip_omits_missing_and_failed_pieces_and_names_them(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    await save(app, application_id, "letter", content="Ma lettre")
    await save(
        app, application_id, "pitch", status="failed", content="",
        meta={"error": "Cette pièce a pris trop de temps : relance le kit pour la refaire."},
    )  # fmt: skip
    _, archive = await fetch(client, application_id)
    assert archive.namelist() == ["02_letter.md", "LISEZMOI.txt"]
    readme = text(archive, "LISEZMOI.txt")
    assert (
        "- 07_pitch.md (Pitch de présentation) : en échec, Cette pièce a pris trop de temps"
        in readme
    )
    assert "- 01_cv.md (CV ciblé) : pas encore produite" in readme
    assert "- 06_company_brief.md (Dossier de l'entreprise) : pas encore produite" in readme


async def test_zip_without_any_piece_still_explains_itself(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    _, archive = await fetch(client, application_id)
    assert archive.namelist() == ["LISEZMOI.txt"]
    assert text(archive, "LISEZMOI.txt").count("pas encore produite") == 7


async def test_zip_says_when_the_cv_pdf_cannot_be_attached(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    await save(
        app,
        application_id,
        "cv",
        content="CV ciblé : version n° 1",
        meta={"version_id": "disparue"},
    )
    _, archive = await fetch(client, application_id)
    assert archive.namelist() == ["01_cv.md", "LISEZMOI.txt"]
    assert "n'a pas pu être jointe" in text(archive, "LISEZMOI.txt")


async def test_zip_filename_is_ascii(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await ready_application(
        client, app, company="Élan Création & Cie", title="Ingénieur·e données/IA (H/F) " + "x" * 80
    )
    await save(app, application_id, "letter")
    r, _ = await fetch(client, application_id)
    name = r.headers["content-disposition"].split('filename="')[1].rstrip('"')
    assert name.isascii() and name.startswith("Kit_Elan_Creation_Cie_") and name.endswith(".zip")
    assert len(name) < 120 and "/" not in name and " " not in name


def test_kit_filename_never_empty() -> None:
    assert kit_filename(COMPANY, "Poste") == "Kit_Societe_Fictive_Poste.zip"
    assert kit_filename("", None) == "Kit.zip"
    assert kit_filename("株式会社", "エンジニア") == "Kit.zip"
