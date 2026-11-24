"""Fictional performance incidents meant for practice."""

from app.features.incident_replay.schemas import IncidentEvent, IncidentScenarioOut

ORDERS = (
    IncidentScenarioOut(
        key="orders-v1",
        title="Overloaded queue",
        context="Order confirmations pile up during a peak period.",
    ),
    [
        IncidentEvent(minute=0, title="Peak begins", observed="The queue holds 120 orders."),
        IncidentEvent(
            minute=4,
            title="Retries multiply",
            observed="The queue exceeds 2,000 orders. The retry rate rises from 2 to 35%.",
        ),
        IncidentEvent(
            minute=9,
            title="Two extra processes start",
            observed="Confirmations decrease. Connections approach the limit.",
        ),
        IncidentEvent(
            minute=14,
            title="Retries are spaced out",
            observed="Pressure on the database drops and the queue gradually empties.",
        ),
    ],
)

CATALOG = (
    IncidentScenarioOut(
        key="catalog-v1",
        title="Catalog stuck after an update",
        context="Published prices stay outdated in some stores.",
    ),
    [
        IncidentEvent(
            minute=0,
            title="Batch published",
            observed="The 400 new prices are present in the reference catalog.",
        ),
        IncidentEvent(
            minute=3,
            title="Stores report a mismatch",
            observed="Two regions still read the previous day's catalog.",
        ),
        IncidentEvent(
            minute=8,
            title="An intermediate cache is identified",
            observed="It expires twelve hours after publication.",
        ),
        IncidentEvent(
            minute=11,
            title="The published version is requested explicitly",
            observed="Prices in both regions match the reference batch.",
        ),
    ],
)

SCENARIOS = {summary.key: (summary, events) for summary, events in (ORDERS, CATALOG)}
