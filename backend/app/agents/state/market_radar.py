"""État du parcours `market_radar` (D159). Le relevé (liens lus, offres extraites, lectures faites)
est en base, derrière le port `RadarStore` : les boucles de lecture et d'extraction le relisent à
chaque passage (SPEC 9.4), l'état ne garde jamais un compteur seul. Il garde seulement les liens
trouvés par la recherche (le port ne les rend pas), l'issue de chaque boucle (calculée sur ce que le
port vient de rendre) et le résumé de `run.completed`."""

from typing import TypedDict


class MarketRadarState(TypedDict, total=False):
    run_id: str
    urls: list[str]  # liens candidats, sans doublon, 80 au plus, dans l'ordre de lecture
    reading_done: bool  # la boucle de lecture n'a plus rien à lire
    extract_done: bool  # la boucle d'extraction n'a plus rien à extraire
    failed_batches: int  # lots d'extraction en panne du fournisseur (l'extraction s'arrête à 2)
    summary: str  # résumé de `run.completed`
