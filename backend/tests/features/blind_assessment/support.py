"""Deux véritables versions de CV de recette avec identifiants à neutraliser."""

from fastapi import FastAPI

from app.agents.tools.cv_schema import CvContent, CvLine, CvSection
from app.db.models.career import CvReview, CvVersion
from tests.features.cv.reviews_support import ready_posting

OWNER_NAME = "Hélène Exemple"
OWNER_MAIL = "helene.exemple@example.org"
OWNER_PHONE = "+33 6 01 02 03 04"
FIRST = "Le service est supervisé avec des alertes contextualisées."
SECOND = "Le service traite 40 dossiers par jour avec un suivi des délais."


def pdf_version(number: int) -> bytes:
    return f"%PDF-1.4\n%Version de recette {number}\n".encode()


async def seed_versions(app: FastAPI, user_id: str) -> tuple[str, str]:
    rt = app.state.career.cv
    posting = await ready_posting(rt, user_id)
    async with rt.session_factory() as db:
        review = CvReview(
            user_id=user_id,
            posting_id=posting,
            template_id="gabarit",
            profile_version=1,
            status="completed",
        )
        db.add(review)
        await db.flush()
        ids = []
        for number, detail in enumerate((FIRST, SECOND), start=1):
            copy = CvContent(
                name=OWNER_NAME,
                headline=f"Ingénieure — {OWNER_NAME}",
                contact=[OWNER_MAIL, OWNER_PHONE],
                sections=[
                    CvSection(
                        key="summary",
                        title="Résumé",
                        items=[CvLine(text=detail), CvLine(text=f"{OWNER_MAIL} ou {OWNER_PHONE}")],
                    )
                ],
            )
            row = CvVersion(
                user_id=user_id,
                review_id=review.id,
                posting_id=posting,
                template_id="gabarit",
                number=number,
                status="ready",
                content=copy.model_dump(),
                filename=f"cv-{number}.pdf",
                storage_key=await rt.storage.save(user_id, "cv", pdf_version(number), ".pdf"),
                original_page_count=1,
                page_count=1,
            )
            db.add(row)
            await db.flush()
            ids.append(row.id)
        await db.commit()
    return ids[0], ids[1]
