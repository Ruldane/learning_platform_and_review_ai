from fastapi import FastAPI

from app.db.base import new_id
from app.db.models.postings import JobPosting

FIRST = "Construire une transformation Python réutilisable."
SECOND = "Documenter et contrôler les valeurs manquantes."
ARTIFACT = "Compte rendu privé avec les résultats des deux cas."


async def seed_posting(app: FastAPI, user_id: str | None = None, *, ready: bool = True) -> str:
    owner = user_id or app.state.local_user_id
    async with app.state.session_factory() as db:
        row = JobPosting(
            user_id=owner,
            source="text",
            text="Description de poste entièrement fictive.",
            text_hash=new_id(),
            title="Ingénierie des données",
            company="Atelier fictif",
            status="ready" if ready else "analyzing",
            analysis={
                "title": "Ingénierie des données",
                "company": "Atelier fictif",
                "level": "junior",
                "location": None,
                "remote": None,
                "language": "fr",
                "requirements": [
                    {"text": FIRST, "required": True, "skills": ["Python"]},
                    {"text": SECOND, "required": False, "skills": ["Qualité des données"]},
                ],
                "keywords": [],
                "eliminatory": [],
                "tools": [],
                "skills": [],
                "apply_url": None,
            }
            if ready
            else None,
        )
        db.add(row)
        await db.commit()
        return str(row.id)
