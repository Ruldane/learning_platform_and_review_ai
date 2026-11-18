"""Déclaration MCP de `cv` : profil maître, gabarits, revues de CV et versions.

Le profil maître ne s'écrit jamais sans January : `PUT /profile` et la confirmation d'un fait
(`PATCH /cv/modifications/{id}`) sont de niveau 3 et portent un contrôle préalable
(`precheck`), dont le verdict est montré sur la carte « À confirmer ». Les PDF et images, et les
téléversements de PDF, sont exclus (pas du JSON)."""

from pydantic import ValidationError

from app.agents.tools.cv_schema import MasterProfileData
from app.features.cv.schemas_profile import ProfilePutIn
from app.mcp.base import FeatureMcp, McpAction, McpGraph, PrecheckInput, Verdict

# Les sources qui viennent d'un document de January ; « january » : écrit à la main (ou par
# Claude), sans document derrière.
DOCUMENT_SOURCES = frozenset({"cv", "linkedin", "note"})

_SECTIONS = (
    ("experiences", "expérience(s)"),
    ("education", "formation(s)"),
    ("skills", "compétence(s)"),
    ("projects", "projet(s)"),
    ("languages", "langue(s)"),
    ("links", "lien(s)"),
)


def unsourced_counts(data: MasterProfileData) -> dict[str, int]:
    """Par section, les faits qu'aucun document de January n'appuie (source « january » seule,
    ou aucune) : ce que le profil doit à une écriture à la main. Jamais le texte des faits."""
    counts: dict[str, int] = {}
    for line_name, label in (("title", "titre"), ("summary", "résumé")):
        line = getattr(data, line_name)
        if line is not None and not DOCUMENT_SOURCES & set(line.sources):
            counts[label] = 1
    for attribute, label in _SECTIONS:
        missing = sum(
            1 for fact in getattr(data, attribute) if not DOCUMENT_SOURCES & set(fact.sources)
        )
        if missing:
            counts[label] = missing
    return counts


async def profile_precheck(request: PrecheckInput) -> Verdict:
    """Contrôle d'honnêteté d'une nouvelle version du profil maître : chaque fait sans source de
    document est signalé (sans le recopier). Le contrôle ne bloque rien : January décide."""
    try:
        body = ProfilePutIn.model_validate(request.body)
    except ValidationError:
        return Verdict(
            ok=False,
            reasons=("Le contenu du profil n'est pas lisible : la route le refusera.",),
            summary="Nouvelle version validée du profil maître (contenu illisible).",
        )
    counts = unsourced_counts(body.data)
    reasons = tuple(f"{n} {label} sans source de document" for label, n in counts.items())
    summary = "Nouvelle version validée du profil maître"
    if body.base_version is not None:
        summary += f", écrite à partir de la version {body.base_version}"
    return Verdict(ok=not reasons, reasons=reasons, summary=f"{summary}.")


async def modification_precheck(request: PrecheckInput) -> Verdict:
    """Une décision sur une modification de CV n'écrit au profil que si `confirm` est vrai : le
    fait « à confirmer » (chiffre, outil ou titre que le profil ne dit pas) y entre alors."""
    body = request.body if isinstance(request.body, dict) else {}
    if body.get("confirm") is True:
        return Verdict(
            ok=False,
            reasons=(
                "Confirmer écrit au profil maître un fait que le profil actuel ne dit pas : "
                "n'accepte que si c'est vrai.",
            ),
            summary="Confirme une modification « à confirmer » : nouvelle version du profil.",
        )
    return Verdict(ok=True, summary="Décision sur une modification de CV, rien n'entre au profil.")


MCP = FeatureMcp(
    feature="cv",
    actions=(
        McpAction(
            "GET /profile", 1, "cv_get_profile", "Le profil maître : version validée et brouillon."
        ),
        McpAction(
            "PUT /profile",
            3,
            "cv_put_profile",
            "Écrit une nouvelle version validée du profil maître (`data`, `base_version`). "
            "Écriture au profil : demande à confirmer, avec un contrôle des faits sans source.",
            side_effects="external",
            precheck=profile_precheck,
        ),
        McpAction(
            "GET /profile/versions", 1, "cv_list_profile_versions", "Les versions du profil maître."
        ),
        McpAction("GET /cv/templates", 1, "cv_list_templates", "Les gabarits de CV non archivés."),
        McpAction(
            "GET /cv/templates/{template_id}",
            1,
            "cv_get_template",
            "Un gabarit de CV, avec son statut et ses pages.",
        ),
        McpAction(
            "POST /cv/templates/{template_id}/activate",
            2,
            "cv_activate_template",
            "Rend ce gabarit le seul actif.",
        ),
        McpAction(
            "DELETE /cv/templates/{template_id}",
            3,
            "cv_archive_template",
            "Archive un gabarit de CV : demande à confirmer.",
        ),
        McpAction(
            "POST /cv/reviews",
            2,
            "cv_start_review",
            "Lance la revue du CV contre une offre (`posting_id`) avec le profil validé et le "
            "gabarit actif.",
            launches="cv_review",
        ),
        McpAction(
            "GET /cv/reviews",
            1,
            "cv_list_reviews",
            "Les revues de CV (d'une offre), récentes d'abord.",
        ),
        McpAction(
            "GET /cv/reviews/{review_id}",
            1,
            "cv_get_review",
            "Une revue de CV : analyse, modifications proposées, décisions.",
        ),
        McpAction(
            "PATCH /cv/reviews/{review_id}/modifications",
            2,
            "cv_decide_modifications",
            "Accepte ou refuse des modifications en groupe (50 au plus) ; les « à confirmer » "
            "ne sont jamais acceptées en groupe.",
        ),
        McpAction(
            "PATCH /cv/modifications/{modification_id}",
            3,
            "cv_decide_modification",
            "Accepte ou refuse une modification (`status`, `after`, `confirm`) ; `confirm` écrit "
            "le fait au profil maître : demande à confirmer, avec contrôle préalable.",
            precheck=modification_precheck,
        ),
        McpAction(
            "POST /cv/reviews/{review_id}/generate",
            3,
            "cv_generate_version",
            "Crée la version du CV ciblé et produit son PDF et ses images (fichiers) : demande "
            "à confirmer.",
            side_effects="external",
        ),
        McpAction("GET /cv/versions", 1, "cv_list_versions", "Les versions du CV ciblé."),
        McpAction(
            "GET /cv/versions/{version_id}",
            1,
            "cv_get_version",
            "Une version du CV ciblé et son statut.",
        ),
    ),
    graphs=(
        McpGraph(
            "cv_review",
            follow_only=True,
            summary="Revue d'un CV contre une offre (`review_id` d'une revue déjà créée).",
        ),
        McpGraph(
            "cv_capture",
            follow_only=True,
            summary="L'Archiviste tire un brouillon de profil (`mode` profile, `document_ids`) "
            "ou le design d'un gabarit (`mode` design, `template_id`) ; January valide.",
        ),
    ),
    play_actions=(
        McpAction(
            "POST /profile/import",
            2,
            "cv_capture_profile",
            "Prépare un brouillon de profil à partir d'un PDF rangé dans Tremplin.",
            body_fields=frozenset({"cv_document_id", "linkedin_document_id", "note"}),
            encoding="form",
            launches="cv_capture",
        ),
        McpAction(
            "POST /cv/templates",
            2,
            "cv_capture_design",
            "Analyse les images d'un PDF rangé dans Tremplin pour en créer un gabarit.",
            body_fields=frozenset({"document_id", "name"}),
            encoding="form",
            launches="cv_capture",
        ),
    ),
    excluded={
        "GET /cv/templates/{template_id}/pages/{kind}/{number}": (
            "Image PNG d'une page, pas du JSON : le MCP lit le gabarit par `cv_get_template`."
        ),
        "GET /cv/versions/{version_id}/pdf": (
            "Téléchargement du PDF (binaire, pas du JSON) : January le télécharge depuis "
            "l'interface ; le MCP lit la version par `cv_get_version`."
        ),
        "GET /cv/versions/{version_id}/pages/{number}": (
            "Image PNG d'une page de version, pas du JSON : le MCP lit la version par "
            "`cv_get_version`."
        ),
    },
)
