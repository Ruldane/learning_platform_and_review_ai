"""Tâche « entretien du MCP » (phase 10, P15, P19) : toutes les 10 minutes et au démarrage, les
demandes « À confirmer » dont l'heure est passée deviennent « expirées » (elles ne s'exécuteront
jamais), et le journal des appels de plus de 30 jours est purgé. Le travail est dans la feature
`mcp` ; la tâche ne fait que déballer son contexte et lire l'heure. Aucun appel au modèle."""

from datetime import UTC, datetime

from app.features.mcp.service.calls import purge_old_calls
from app.features.mcp.service.confirmations import expire_due
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    now = datetime.now(UTC)
    await expire_due(ctx.session_factory, now)
    await purge_old_calls(ctx.session_factory, now)
