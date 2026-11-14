"""Port des gabarits vu par le Maquettiste (`CvTemplateStore`, D125, D126).

La mise en page du CV d'origine est extraite **une fois**, à la création du gabarit (la route
refuse un PDF illisible avant de lancer quoi que ce soit) : images des pages rangées, géométrie,
blocs résumés, texte visible et rôles des polices dans `cv_templates.prepared`. `prepare` y
ajoute les polices (téléchargées une fois, réutilisées d'un gabarit à l'autre), puis n'est plus
qu'une relecture. `render_pass` est idempotent par `(gabarit, passe)` : une passe rangée dans
`pass_log` est relue, jamais rendue deux fois ; la passe rendue devient la passe courante du
gabarit (spec, HTML, CSS, score, zones, images), celle que `finish(ready)` garde.

Journaux : identifiants et nombres seulement, jamais un texte, une image ni une police du CV."""

import logging
from typing import Any

from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.agents.tools.cv_template_port import (
    OriginalView,
    PassResult,
    TemplateOutcome,
    keeps_pass,
)
from app.agents.tools.template_schema import TemplateSpec
from app.agents.tools.template_similarity import similarity
from app.core.errors import AppError
from app.db.models.career import CvTemplate
from app.features.cv.repository import ProfileRepository, TemplateRepository
from app.features.cv.service.fonts import (
    StoredFont,
    available_families,
    load_files,
    offered_choices,
    offered_summary,
    resolve_roles,
    roles_from_json,
)
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.template import cv_document
from app.features.cv.service.templates_data import (
    original_pages,
    profile_content,
    similarity_from_json,
    similarity_to_json,
    template_not_found,
)

logger = logging.getLogger(__name__)

IMAGE_CATEGORY = "cv_templates"
MAX_REASON_CHARS = 300


def pass_not_found() -> AppError:
    return AppError("template_pass_not_found", "Passe du modèle introuvable.", 404)


def capture_over() -> AppError:
    return AppError("template_not_capturing", "La capture de ce modèle est terminée.", 409)


class AgentCvTemplateStore:
    """`CvTemplateStore` de la composition (`app.bootstrap_career`)."""

    def __init__(self, runtime: CvRuntime) -> None:
        self._rt = runtime

    async def _row(self, user_id: str, template_id: str) -> CvTemplate:
        async with self._rt.session_factory() as db:
            row = await TemplateRepository(db, user_id).get(template_id)
        if row is None or row.prepared is None or row.status == "archived":
            raise template_not_found()
        return row

    async def _images(self, user_id: str, keys: list[Any]) -> list[bytes]:
        return [await self._rt.storage.read(user_id, str(key)) for key in keys]

    async def _fonts(self, user_id: str, row: CvTemplate) -> dict[str, Any]:
        """Polices résolues une seule fois par gabarit, puis relues telles quelles."""
        prepared = dict(row.prepared or {})
        if "font_files" in prepared:
            return prepared
        roles = roles_from_json(prepared.get("roles", []))
        stored, uses, gaps = await resolve_roles(self._rt, user_id, roles)
        prepared["font_files"] = [font.to_json() for font in stored]
        async with self._rt.session_factory() as db:
            repo = TemplateRepository(db, user_id)
            fresh = await repo.get(row.id)
            if fresh is None:
                raise template_not_found()
            if "font_files" in (fresh.prepared or {}):  # déjà résolues entre-temps
                return dict(fresh.prepared or {})
            fresh.prepared = prepared
            fresh.fonts = [use.model_dump() for use in uses]
            fresh.font_gaps = gaps
            await db.commit()
        return prepared

    async def prepare(self, user_id: str, template_id: str) -> OriginalView:
        row = await self._row(user_id, template_id)
        prepared = await self._fonts(user_id, row)
        stored = [StoredFont.from_json(f) for f in prepared["font_files"]]
        roles = roles_from_json(prepared.get("roles", []))
        available = available_families(stored)
        return OriginalView(
            template_id=row.id,
            page_count=row.page_count,
            page_size=(float(row.page_size["width_pt"]), float(row.page_size["height_pt"])),
            selectable=row.selectable,
            pages_png=await self._images(user_id, row.original_pages),
            blocks_summary=offered_summary(str(prepared.get("blocks_summary", "")), available),
            fonts=offered_choices(roles, available),
            available_fonts=available,
            original_text=str(prepared.get("original_text", "")),
        )

    async def sample_fallback(self, user_id: str) -> CvContent | None:
        async with self._rt.session_factory() as db:
            row = await ProfileRepository(db, user_id).latest("validated")
        if row is None:
            return None
        return profile_content(MasterProfileData.model_validate(row.data))

    async def _stored_pass(self, user_id: str, row: CvTemplate, pass_no: int) -> PassResult | None:
        for entry in row.pass_log:
            if entry["pass_no"] == pass_no:
                images = await self._images(user_id, entry["render_pages"])
                sim = similarity_from_json(entry["similarity"])
                return PassResult(pass_no, int(entry["score"]), sim, images)
        return None

    async def read_pass(self, user_id: str, template_id: str, pass_no: int) -> PassResult:
        row = await self._row(user_id, template_id)
        done = await self._stored_pass(user_id, row, pass_no)
        if done is None:
            raise pass_not_found()
        return done

    async def _store_pass(
        self,
        user_id: str,
        template_id: str,
        entry: dict[str, Any],
        current: dict[str, Any],
        adjusted: bool,
    ) -> bool:
        """La passe entre dans le journal ; elle devient la passe courante (colonnes `current`)
        seulement si `keeps_pass` : la meilleure fait le gabarit (D125)."""
        async with self._rt.session_factory() as db:
            fresh = await TemplateRepository(db, user_id).get(template_id)
            if fresh is None:
                raise template_not_found()
            if fresh.status == "failed":
                raise capture_over()
            fresh.pass_log = [*fresh.pass_log, entry]
            fresh.passes = max(fresh.passes, entry["pass_no"])
            kept = keeps_pass(adjusted, entry["score"], fresh.score)
            if kept:
                for column, value in current.items():
                    setattr(fresh, column, value)
            await db.commit()
        return kept

    async def render_pass(
        self,
        user_id: str,
        template_id: str,
        pass_no: int,
        spec: TemplateSpec,
        content: CvContent,
        adjusted: bool = False,
    ) -> PassResult:
        row = await self._row(user_id, template_id)
        if row.status == "failed":  # session annulée pendant un rendu : rien n'est rangé (M2)
            raise capture_over()
        if (done := await self._stored_pass(user_id, row, pass_no)) is not None:
            return done
        prepared = await self._fonts(user_id, row)
        stored = [StoredFont.from_json(f) for f in prepared["font_files"]]
        fonts = await load_files(self._rt, user_id, stored, {spec.fonts.body, spec.fonts.heading})
        document = cv_document(spec, content, fonts)
        pdf = await self._rt.html_pdf.html_to_pdf(document)
        render = await self._rt.layout.extract_layout(pdf)
        original = original_pages(
            prepared["pages"], await self._images(user_id, row.original_pages)
        )
        sim = similarity(original, render.pages)
        images = [page.image_png for page in render.pages]
        keys = [await self._rt.storage.save(user_id, IMAGE_CATEGORY, png, ".png") for png in images]
        detail = similarity_to_json(sim)
        entry = {"pass_no": pass_no, "score": sim.score, "similarity": detail, "render_pages": keys}
        current = {
            "spec": spec.model_dump(mode="json"),
            "html": document.index_html,
            "css": document.assets["cv.css"].decode(),
            "score": sim.score,
            "score_detail": detail,
            "render_pages": keys,
            "sample_content": content.model_dump(mode="json"),
        }
        kept = await self._store_pass(user_id, template_id, entry, current, adjusted)
        logger.info(
            "Passe rangée : utilisateur %s, gabarit %s, passe %d, score %d, %d page(s), gardée %s",
            user_id,
            template_id,
            pass_no,
            sim.score,
            len(keys),
            kept,
        )
        return PassResult(pass_no, sim.score, sim, images)

    async def finish(
        self, user_id: str, template_id: str, status: TemplateOutcome, reason: str | None
    ) -> None:
        """Idempotent ; un gabarit prêt ou archivé ne change plus."""
        async with self._rt.template_lock(user_id), self._rt.session_factory() as db:
            repo = TemplateRepository(db, user_id)
            row = await repo.get(template_id)
            if row is None:
                raise template_not_found()
            if row.status in ("ready", "archived"):
                return
            if row.status == "failed":  # figé : `failed` redit est sans effet, `ready` refusé
                if status == "ready":
                    raise capture_over()
                return
            if status == "ready":
                row.status, row.failure_reason = "ready", None
                row.active = await repo.active() is None
            else:
                row.status = "failed"
                row.failure_reason = (reason or "La capture du modèle a échoué.")[:MAX_REASON_CHARS]
            active = row.active
            await db.commit()
        logger.info(
            "Gabarit %s : utilisateur %s, gabarit %s, actif %s",
            status,
            user_id,
            template_id,
            active,
        )
