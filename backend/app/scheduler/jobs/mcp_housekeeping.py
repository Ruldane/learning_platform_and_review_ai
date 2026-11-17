"""Tâche « entretien du MCP » (phase 10, P15, P19) : toutes les 10 minutes et au démarrage, les
demandes « À confirmer » dont l'heure est passée deviennent « expirées » (elles ne s'exécuteront
jamais), puis le journal des appels, l'historique des changements et les demandes closes de plus de
30 jours sont purgés (ils gardent du texte : rien n'y reste au-delà). Elle rattrape aussi
l'indexation des éléments de mémoire restés à `indexed_at` vide (écritures directes du MCP, après
un redémarrage avant la tâche de fond), par lots bornés : seulement les embeddings, aucun appel
au modèle. Le travail est dans les features `mcp` et `memory` ; la tâche ne fait que déballer son
contexte et lire l'heure."""

from datetime import UTC, datetime

from app.features.mcp.service.calls import purge_old_calls
from app.features.mcp.service.changes import purge_old_changes
from app.features.mcp.service.confirmation_support import purge_closed_confirmations
from app.features.mcp.service.confirmations import expire_due
from app.features.memory.service.direct import index_pending_all
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    now = datetime.now(UTC)
    await expire_due(ctx.session_factory, now)
    await purge_old_calls(ctx.session_factory, now)
    await purge_old_changes(ctx.session_factory, now)
    await purge_closed_confirmations(ctx.session_factory, now)
    # La mémoire que le quotidien porte déjà (projets) : rien à changer à `JobContext`.
    await index_pending_all(ctx.daily.projects.memory)
