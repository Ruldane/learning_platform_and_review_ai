"""Les pièces du kit vues par l'API (D143) : une ligne `kit_items` devient un `KitItemOut`, et le
texte qu'January modifie est recontrôlé par le code (`text_claims`, comme à la rédaction : SPEC 1,
18.3). Fonctions pures.

Conventions du contenu rangé (D142) : `followups` = courriel de 7 jours, une ligne `---`,
courriel de 14 jours ; `linkedin` = invitation, une ligne `---`, message ; `form_answers` =
`### question` puis la réponse (« À remplir par toi » ou « À compléter » si le code l'a vidée)."""

import re
from dataclasses import dataclass
from typing import cast

from app.agents.nodes.tracker.honesty import allowed_phrases
from app.agents.tools.kit_schema import (
    NO_QUESTION,
    SALARY_BLANK,
    TO_COMPLETE,
    KitContext,
    split_followups,
    split_parts,
)
from app.agents.tools.salary import is_salary_question
from app.agents.tools.text_claims import text_claims
from app.db.models.applications import KitItem
from app.features.applications.schemas_kit import KitItemOut, KitKind, KitSourceOut, KitStatus

CHECKED: frozenset[str] = frozenset({"letter", "linkedin", "followups", "form_answers", "pitch"})
_QUESTION = re.compile(r"^### +(.*)$")
_BLANKS = frozenset({SALARY_BLANK, TO_COMPLETE})


def pending_item(kind: KitKind) -> KitItemOut:
    """Une pièce pas encore rangée."""
    return KitItemOut(
        id=None,
        kind=kind,
        status="pending",
        content="",
        flags=[],
        salary_fields=0,
        words=None,
        error=None,
        sources=[],
        edited=False,
        updated_at=None,
    )


def form_items(content: str) -> list[tuple[str, str]]:
    """`(question, réponse)` d'un `form_answers` (le texte sous chaque `### question`) ; sans
    titre, tout le texte est une réponse sans question."""
    items: list[tuple[str, list[str]]] = []
    for line in content.splitlines():
        if match := _QUESTION.match(line):
            items.append((match.group(1).strip(), []))
        elif items:
            items[-1][1].append(line)
    if not items:
        text = content.strip()
        return [("", text)] if text and text != NO_QUESTION else []
    return [(question, "\n".join(lines).strip()) for question, lines in items]


def form_bodies(content: str) -> list[str]:
    return [body for _, body in form_items(content)]


def salary_fields(content: str) -> int:
    """Les réponses laissées à January parce qu'elles engagent sa prétention salariale."""
    return sum(1 for body in form_bodies(content) if body == SALARY_BLANK)


def words_of(kind: str, content: str) -> int | dict[str, int] | None:
    """Le compte de mots rangé dans `meta.words` (même forme qu'à la rédaction)."""
    if kind in ("letter", "pitch"):
        return len(content.split())
    if kind == "linkedin":
        return len(split_parts(content)[-1].split())
    if kind == "followups":
        day_7, day_14 = split_followups(content)
        return {"day_7": len(day_7.split()), "day_14": len(day_14.split())}
    return None


def total_words(words: object) -> int | None:
    if isinstance(words, bool):
        return None
    if isinstance(words, int):
        return words
    if isinstance(words, dict):
        return sum(value for value in words.values() if isinstance(value, int))
    return None


def sources_of(meta: dict[str, object]) -> list[KitSourceOut]:
    """Les pages du dossier rangées avec la pièce, dans l'ordre des citations `[n]`."""
    refs = meta.get("source_refs")
    if not isinstance(refs, list):
        return []
    return [
        KitSourceOut(rank=rank, url=str(ref.get("url", "")), title=ref.get("title") or None)
        for rank, ref in enumerate(refs, 1)
        if isinstance(ref, dict)
    ]


def item_out(row: KitItem) -> KitItemOut:
    meta = dict(row.meta or {})
    flags = meta.get("flags")
    error = meta.get("error")
    return KitItemOut(
        id=row.id,
        kind=cast(KitKind, row.kind),  # la colonne est un texte, les valeurs sont KitKind
        status=cast(KitStatus, row.status),
        content=row.content,
        flags=[str(flag) for flag in flags] if isinstance(flags, list) else [],
        salary_fields=salary_fields(row.content) if row.kind == "form_answers" else 0,
        words=total_words(meta.get("words")),
        error=str(error) if row.status == "failed" and error else None,
        sources=sources_of(meta) if row.kind == "company_brief" else [],
        edited=row.edited,
        updated_at=row.updated_at,
    )


def texts_to_check(kind: str, content: str) -> list[str]:
    """Les textes de January que `text_claims` relit : jamais les questions du formulaire."""
    if kind in ("linkedin", "followups"):
        return split_parts(content)
    if kind == "form_answers":
        # La prétention salariale est celle de January : aucun fait du profil ne la dit.
        return [
            body
            for question, body in form_items(content)
            if body not in _BLANKS and not is_salary_question(question)
        ]
    return [content]


def has_blank(kind: str, content: str) -> bool:
    """Une réponse du formulaire reste à remplir ou à compléter."""
    return kind == "form_answers" and any(body in _BLANKS for body in form_bodies(content))


def flagged(kind: str, content: str, ctx: KitContext) -> list[str]:
    """Les termes (chiffres, outils, titres, noms) que le profil ne dit pas, sans doublon. Pour
    une pièce hors `CHECKED`, aucun : le dossier vient du web, le CV n'est pas un texte écrit."""
    if kind not in CHECKED:
        return []
    allowed = allowed_phrases(ctx)
    terms: list[str] = []
    for text in texts_to_check(kind, content):
        for claim in text_claims(text, ctx.profile, allowed=allowed):
            if claim.term not in terms:
                terms.append(claim.term)
    return terms


@dataclass(frozen=True)
class Rechecked:
    status: KitStatus
    meta: dict[str, object]


def needs_context(status: str, content: str) -> bool:
    """La pièce sera relue : une pièce prête avec du texte ne l'est pas."""
    return not (status == "ready" and content.strip())


def recheck(row: KitItem, content: str, ctx: KitContext | None) -> Rechecked:
    """Le statut et le `meta` après la modification de January. Une pièce « à vérifier » (ou en
    échec, qu'elle remplit) est relue par `text_claims` : `flags` mis à jour, « prête » si rien ne
    reste (ni terme, ni réponse à remplir) ; une pièce prête reste prête. Un texte vide est
    toujours « à vérifier »."""
    meta = {key: value for key, value in (row.meta or {}).items() if key not in ("error", "code")}
    words = words_of(row.kind, content)
    if words is not None:
        meta["words"] = words
    if not needs_context(row.status, content):
        return Rechecked("ready", meta)
    if ctx is None:
        raise ValueError("Le contexte du kit est nécessaire pour relire une pièce.")
    terms = flagged(row.kind, content, ctx)
    if terms:
        meta["flags"] = terms
    else:
        meta.pop("flags", None)
    clean = content.strip() and not terms and not has_blank(row.kind, content)
    return Rechecked("ready" if clean else "to_check", meta)
