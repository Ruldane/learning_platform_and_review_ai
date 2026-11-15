"""Délais des relances (SPEC 6.2, D138) : trois jours strictement croissants après la
candidature. Fonction pure, lue par `UserSettings` (validation) et par les règles de relance des
candidatures (`applications.service.schedule`, qui importe `settings.service` : un seul sens)."""

from collections.abc import Sequence

DEFAULT_DELAYS = (7, 14, 21)
MIN_DELAY, MAX_DELAY = 1, 90


def validated_delays(raw: Sequence[int]) -> tuple[int, int, int]:
    """Les délais des trois relances d'attente (jours après la candidature) : trois entiers
    strictement croissants de 1 à 90, sinon (7, 14, 21)."""
    ok = (
        len(raw) == len(DEFAULT_DELAYS)
        and all(isinstance(n, int) and not isinstance(n, bool) for n in raw)
        and all(MIN_DELAY <= n <= MAX_DELAY for n in raw)
        and all(a < b for a, b in zip(raw, raw[1:], strict=False))
    )
    return (raw[0], raw[1], raw[2]) if ok else DEFAULT_DELAYS
