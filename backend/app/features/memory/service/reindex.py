"""Réindexation de la mémoire d'un utilisateur (4.6, D67) : l'index Qdrant est reconstruit à
partir du texte, qui fait foi en base ; les fragments sont recalculés au passage. Exécutée par le
worker (`jobs.py`), en série avec les imports : aucun import ne tourne en même temps.

Jamais de transaction SQLite ouverte pendant un appel à Ollama ou à Qdrant, jamais le verrou
asyncio de l'utilisateur tenu pendant une attente de SQLite (D66) :

1. drapeau `reindexing` levé : un `index_item` qui commence ensuite renouvelle ses fragments
   sans toucher l'index et laisse l'élément non indexé ; on attend la fin de ceux déjà lancés ;
2. `clear_indexed` (transaction courte), puis `delete_user` sous le verrou de l'utilisateur ;
3. par lots de 16 : fragments préparés et validés, poussés (verrou pris et rendu par élément
   dans `push`), puis `indexed_at` posé si les fragments n'ont pas changé entre-temps ;
4. fin quand un lot est vide et qu'aucun écrivain n'a agi depuis sa lecture : le drapeau est
   baissé dans le même pas synchrone. Panne d'Ollama ou de Qdrant : l'erreur du port remonte
   (message lisible), les éléments restants gardent `indexed_at` nul.

Les journaux ne citent que des identifiants et des nombres."""

import logging
from collections.abc import Callable

from app.features.memory.repository import MemoryItemRepository
from app.features.memory.schemas import ReindexState
from app.features.memory.service.runtime import MemoryRuntime

logger = logging.getLogger(__name__)

BATCH_SIZE = 16

Report = Callable[[ReindexState], None]


def running(done: int, total: int) -> ReindexState:
    return ReindexState(status="running", done=done, total=max(total, done), error=None)


async def reindex_user(runtime: MemoryRuntime, user_id: str, report: Report) -> None:
    """Reconstruit l'index de l'utilisateur et rend compte de l'avancement (`report`) ; l'état
    final `done` est rapporté ici. Une panne lève l'erreur du port : l'appelant la rapporte."""
    indexer = runtime.indexer
    indexer.begin_reindex(user_id)
    try:
        total = await _reset(runtime, user_id)
        report(running(0, total))
        done = await _rebuild(runtime, user_id, total, report)
    finally:
        indexer.end_reindex(user_id)
    report(ReindexState(status="done", done=done, total=max(total, done), error=None))
    logger.info("Réindexation de %s terminée : %d élément(s)", user_id, done)


async def _reset(runtime: MemoryRuntime, user_id: str) -> int:
    """Étapes 1 et 2 : écrivains en cours terminés, tout marqué à réindexer, vecteurs effacés.
    Rend le nombre d'éléments à réindexer."""
    await runtime.indexer.wait_writers(user_id)
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, user_id)
        await items.clear_indexed()
        await db.commit()
        total = await items.count_unindexed()
        await db.commit()
    async with runtime.indexer.lock(user_id):
        await runtime.providers.index.delete_user(user_id)
    return total


async def _rebuild(runtime: MemoryRuntime, user_id: str, total: int, report: Report) -> int:
    """Étapes 3 et 4 : lots jusqu'à épuisement. Rend le nombre d'éléments indexés."""
    indexer, done = runtime.indexer, 0
    while True:
        generation = indexer.writers_generation(user_id)
        marked, read = await _batch(runtime, user_id)
        if read:
            done += marked
            report(running(done, total))
            continue
        if indexer.writers_settled(user_id, generation):
            indexer.end_reindex(user_id)  # sans `await` depuis le constat : rien n'a pu passer
            return done
        await indexer.wait_writers(user_id)


async def _batch(runtime: MemoryRuntime, user_id: str) -> tuple[int, int]:
    """Un lot : `(éléments marqués indexés, éléments lus)`. Le verrou d'écriture de SQLite est
    pris avant la lecture (pas de passage lecture → écriture refusé par SQLite) et rendu avant
    la vectorisation."""
    indexer = runtime.indexer
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, user_id)
        await items.begin_write()
        batch = await items.unindexed_batch(BATCH_SIZE)
        prepared = [(item, await indexer.prepare(db, item)) for item in batch]
        await db.commit()
        for item, chunks in prepared:
            await indexer.push(user_id, item.id, chunks)
        marked = await indexer.mark_indexed(db, user_id, prepared) if prepared else 0
    return marked, len(batch)
