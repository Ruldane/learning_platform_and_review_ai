"""Incidents de performance fictifs destinés à l'entraînement."""

from app.features.incident_replay.schemas import IncidentEvent, IncidentScenarioOut

ORDERS = (
    IncidentScenarioOut(
        key="orders-v1",
        title="File d’attente en surcharge",
        context="Les confirmations de commande s’accumulent pendant une période de pointe.",
    ),
    [
        IncidentEvent(
            minute=0, title="Début de la pointe", observed="La file contient 120 commandes."
        ),
        IncidentEvent(
            minute=4,
            title="Les reprises se multiplient",
            observed="La file dépasse 2 000 commandes. Le taux de reprise passe de 2 à 35 %.",
        ),
        IncidentEvent(
            minute=9,
            title="Deux processus supplémentaires démarrent",
            observed="Les confirmations diminuent. Les connexions approchent de la limite.",
        ),
        IncidentEvent(
            minute=14,
            title="Les reprises sont espacées",
            observed="La pression sur la base diminue et la file se vide progressivement.",
        ),
    ],
)

CATALOG = (
    IncidentScenarioOut(
        key="catalog-v1",
        title="Catalogue figé après une mise à jour",
        context="Les prix publiés restent anciens dans certains magasins.",
    ),
    [
        IncidentEvent(
            minute=0,
            title="Publication du lot",
            observed="Les 400 nouveaux prix sont présents dans le catalogue de référence.",
        ),
        IncidentEvent(
            minute=3,
            title="Les magasins signalent un écart",
            observed="Deux régions lisent toujours le catalogue de la veille.",
        ),
        IncidentEvent(
            minute=8,
            title="Une mise en cache intermédiaire est identifiée",
            observed="Son expiration arrive douze heures après la publication.",
        ),
        IncidentEvent(
            minute=11,
            title="La version publiée est demandée explicitement",
            observed="Les prix des deux régions correspondent au lot de référence.",
        ),
    ],
)

SCENARIOS = {summary.key: (summary, events) for summary, events in (ORDERS, CATALOG)}
