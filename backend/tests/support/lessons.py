"""Faux port des leçons (`FakeLessonStore`) en mémoire, idempotent comme le contrat, et fabrique de
leçons Markdown valides (`lesson_markdown`) pour les tests du Vérificateur et du parcours
`lesson_factory`. Aucun réseau ni LLM."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import uuid4

from app.agents.nodes.verifier.checks import check_lesson
from app.agents.tools.lesson_port import (
    LessonReport,
    ModuleBrief,
    PublishedLesson,
    ResourcePick,
)
from app.core.errors import AppError

PROGRAM_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000001"
MODULE_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000002"
OTHER_MODULE_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000003"
TITLE = "Attention multi-têtes"
URL_ONE = "https://site0.exemple.org/article"
URL_TWO = "https://site1.exemple.org/article"
SOURCE_ONE = (
    "L'attention calcule pour chaque position une moyenne pondérée des valeurs de toutes les "
    "positions de la séquence. Les poids viennent d'un produit scalaire entre une requête et "
    "des clés, normalisé par la racine de la dimension puis passé dans une fonction softmax. "
    "Plusieurs têtes travaillent en parallèle sur des projections différentes avant d'être "
    "concaténées et projetées une dernière fois."
)
SOURCE_TWO = "Le masque causal empêche une position de regarder les positions futures."
SOURCES = [(1, URL_ONE, SOURCE_ONE), (2, URL_TWO, SOURCE_TWO)]

_DIAGRAM = 'flowchart TD\n    A["Requête"] --> B["Poids"]\n    B --> C["Somme pondérée"]'


_HEAD = """# {title}

## Objectifs

- Comprendre le calcul des poids d'attention [1].
- Savoir lire un masque causal [2].

## Prérequis

Les produits matriciels et la fonction softmax.

## L'essentiel en 5 lignes

- L'attention pondère les positions [1].
- Les poids viennent d'un produit scalaire [1].
- Plusieurs têtes travaillent en parallèle [1].
- Le masque causal cache le futur [2].
- Les têtes sont concaténées puis projetées [1].

## Explication

"""
_TAIL = """## Exemple travaillé

Prenons trois positions et calculons les poids à la main, étape par étape.

## Erreurs fréquentes

Oublier la normalisation par la racine de la dimension.

## Exercice

Calculer les poids d'attention d'une séquence de trois mots.

## Corrigé de l'exercice

Les poids valent une distribution de probabilité sur les trois positions.

## Sources

1. [Premier article]({one})
2. [Second article]({two})

## Auto-évaluation

1. Que calcule la requête ?
2. Pourquoi normaliser par la racine ?
3. À quoi sert une tête ?
4. Que cache le masque causal ?
5. Comment les têtes sont-elles combinées ?
"""


def _skeleton(title: str, urls: tuple[str, str], filler: str) -> str:
    nl = chr(10)
    diagram = nl.join(["## Schémas", "", "```mermaid", _DIAGRAM, "```", "", ""])
    tail = _TAIL.format(one=urls[0], two=urls[1])
    return _HEAD.format(title=title) + filler + nl + nl + diagram + tail


def lesson_markdown(
    words: int = 1500, *, title: str = TITLE, urls: tuple[str, str] = (URL_ONE, URL_TWO)
) -> str:
    """Leçon valide de `words` mots exactement (blocs de code exclus), citant `[1]` et `[2]`,
    liée à `urls`. `words` doit dépasser la taille du squelette (environ 150 mots)."""
    base = check_lesson(_skeleton(title, urls, ""), title=title, sources=[]).words
    filler = " ".join(f"notion{n}" for n in range(max(0, words - base)))
    return _skeleton(title, urls, filler)


@dataclass(frozen=True)
class PublishedRecord:
    session_id: str
    module_id: str
    lesson_id: str
    markdown: str
    resources: tuple[ResourcePick, ...]
    report: LessonReport


@dataclass
class FakeLessonStore:
    """`briefs` : (utilisateur, module) → fiche ; une fiche d'un autre utilisateur est introuvable
    (404). `published` : leçons rangées, une par module (rejoué : la même) ; `publish_calls`
    compte tous les appels. `failures` : `(module, raison)` ; `next_calls` : `(programme, session)`
    de chaque appel de `next_module`, qui rend `next_result`. `block_after_publish` fige l'appel
    après l'écriture (arrêt du back en plein nœud)."""

    briefs: dict[tuple[str, str], ModuleBrief] = field(default_factory=dict)
    published: list[PublishedRecord] = field(default_factory=list)
    publish_calls: int = 0
    block_after_publish: bool = False
    failures: list[tuple[str, str]] = field(default_factory=list)
    fail_calls: int = 0
    next_calls: list[tuple[str, str]] = field(default_factory=list)
    next_result: str | None = None
    pdf_ok: bool = True

    def add_module(
        self, user_id: str, *, module_id: str = MODULE_ID, seeds: tuple[str, ...] = ()
    ) -> ModuleBrief:
        brief = ModuleBrief(
            module_id=module_id,
            program_id=PROGRAM_ID,
            title=TITLE,
            skills=("Attention", "Transformers"),
            prerequisites=("Algèbre linéaire",),
            week_rank=1,
            week_theme="Les bases des modèles de langage",
            goal_text="Devenir AI product engineer",
            language="fr",
            seed_urls=seeds,
        )
        self.briefs[(user_id, module_id)] = brief
        return brief

    async def brief(self, user_id: str, module_id: str) -> ModuleBrief:
        found = self.briefs.get((user_id, module_id))
        if found is None:
            raise AppError("module_not_found", "Module introuvable.", 404)
        return found

    async def publish(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        *,
        markdown: str,
        resources: Sequence[ResourcePick],
        report: LessonReport,
    ) -> PublishedLesson:
        await self.brief(user_id, module_id)
        self.publish_calls += 1
        done = next((p for p in self.published if p.module_id == module_id), None)
        if done is None:
            done = PublishedRecord(
                session_id, module_id, uuid4().hex, markdown, tuple(resources), report
            )
            self.published.append(done)
        if self.block_after_publish:
            await asyncio.Event().wait()
        return PublishedLesson(done.lesson_id, self.pdf_ok, len(done.resources))

    async def fail(self, user_id: str, session_id: str, module_id: str, reason: str) -> None:
        await self.brief(user_id, module_id)
        self.fail_calls += 1
        if all(module != module_id for module, _ in self.failures):
            self.failures.append((module_id, reason))

    async def next_module(
        self, user_id: str, program_id: str, *, exclude_session_id: str
    ) -> str | None:
        self.next_calls.append((program_id, exclude_session_id))
        return self.next_result
