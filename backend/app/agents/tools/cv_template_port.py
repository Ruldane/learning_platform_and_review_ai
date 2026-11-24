"""Port des gabarits de CV (D125) : ce que le Maquettiste (`cv_capture`, mode `design`) emprunte
à la feature `cv` (`AgentCvTemplateStore`, 6.10), sans l'importer (contrat 6).

Chaque écriture est **idempotente** (SPEC 9.4) : `prepare` par gabarit, `render_pass` par
`(gabarit, passe)` (une passe déjà rendue est relue, jamais rendue deux fois), `finish` par
gabarit. `read_pass` relit une passe rangée sans aucun rendu : le nœud `fix` y prend les images
du rendu, que l'état du graphe ne garde pas (les checkpoints restent légers).

Le texte et les images d'un CV, les noms de polices lus dans le PDF sont des données
personnelles : ni journal, ni message d'erreur."""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.agents.tools.cv_schema import CvContent
from app.agents.tools.template_schema import TemplateSpec
from app.agents.tools.template_similarity import Similarity
from app.core.errors import AppError
from app.providers.fonts.catalog import FontChoice

TemplateOutcome = Literal["ready", "failed"]


@dataclass(frozen=True)
class OriginalView:
    """Le CV d'origine tel que le Maquettiste le voit. `blocks_summary` : une ligne par bloc,
    « x,y,l,h | police | taille | couleur | gras | texte » ; `fonts` : polices libres choisies pour
    celles du PDF (`FontChoice`) ; `available_fonts` : familles qu'un `TemplateSpec` peut citer ;
    `original_text` : texte visible dans l'ordre du flux (contrôle des lignes recopiées)."""

    template_id: str
    page_count: int
    page_size: tuple[float, float]  # largeur, hauteur en points
    selectable: bool  # faux : CV scanné, sans texte
    pages_png: list[bytes]
    blocks_summary: str
    fonts: list[FontChoice]
    available_fonts: list[str]
    original_text: str


@dataclass(frozen=True)
class PassResult:
    pass_no: int
    score: int
    similarity: Similarity
    render_png: list[bytes]


def keeps_pass(adjusted: bool, score: int, kept_score: int | None) -> bool:
    """La passe rendue devient-elle la passe gardée du gabarit ? Parmi les passes automatiques,
    la meilleure l'emporte (à égalité, la plus récente) : 69, 78, 69 garde la passe 2. Une passe
    d'ajustement suit la consigne de January, que le score ne voit pas : elle remplace toujours.
    Règle commune au port réel, au faux et au graphe : le score montré est celui de la passe
    gardée."""
    return kept_score is None or adjusted or score >= kept_score


class CvTemplateStore(Protocol):
    async def prepare(self, user_id: str, template_id: str) -> OriginalView:
        """Idempotent : mise en page (6.3), images rangées, polices choisies et téléchargées,
        écarts notés ; relu tel quel ensuite. Gabarit absent ou d'une autre : 404."""
        ...

    async def sample_fallback(self, user_id: str) -> CvContent | None:
        """Contenu de démonstration tiré du profil validé (CV scanné) ; `None` sans profil."""
        ...

    async def render_pass(
        self,
        user_id: str,
        template_id: str,
        pass_no: int,
        spec: TemplateSpec,
        content: CvContent,
        adjusted: bool = False,
    ) -> PassResult:
        """Idempotent par `(template_id, pass_no)` : passe déjà rendue → relue sans nouveau
        rendu ; sinon `cv_document`, `html_to_pdf`, extraction du rendu, `similarity`, rangement
        (spec, html, css, score, zones, images) de la passe seulement si `keeps_pass` ; la passe
        reste dans le journal des passes dans tous les cas."""
        ...

    async def read_pass(self, user_id: str, template_id: str, pass_no: int) -> PassResult:
        """Une passe déjà rangée, relue sans aucun rendu ; 404 si elle n'existe pas."""
        ...

    async def finish(
        self, user_id: str, template_id: str, status: TemplateOutcome, reason: str | None
    ) -> None:
        """`ready` : la passe gardée (`keeps_pass`) devient le gabarit, actif si aucun
        autre ne l'est ; `failed` : `reason` (phrase française, sans donnée du CV) rangée.
        Idempotent ; un gabarit `failed` ne passe plus à `ready` (409 `template_not_capturing`)."""
        ...


def cv_templates_unavailable() -> AppError:
    return AppError(
        "cv_templates_unavailable", "CV templates are unavailable in this runtime.", 503
    )


class _NoCvTemplates:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def prepare(self, user_id: str, template_id: str) -> OriginalView:
        raise cv_templates_unavailable()

    async def sample_fallback(self, user_id: str) -> CvContent | None:
        raise cv_templates_unavailable()

    async def render_pass(
        self,
        user_id: str,
        template_id: str,
        pass_no: int,
        spec: TemplateSpec,
        content: CvContent,
        adjusted: bool = False,
    ) -> PassResult:
        raise cv_templates_unavailable()

    async def read_pass(self, user_id: str, template_id: str, pass_no: int) -> PassResult:
        raise cv_templates_unavailable()

    async def finish(
        self, user_id: str, template_id: str, status: TemplateOutcome, reason: str | None
    ) -> None:
        raise cv_templates_unavailable()


NO_CV_TEMPLATES: CvTemplateStore = _NoCvTemplates()
