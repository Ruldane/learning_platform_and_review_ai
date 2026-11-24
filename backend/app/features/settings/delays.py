"""Follow-up delays (SPEC 6.2, D138): three strictly increasing days after the application.
Pure function, read by `UserSettings` (validation) and by the application follow-up rules
(`applications.service.schedule`, which imports `settings.service`: one direction only)."""

from collections.abc import Sequence

DEFAULT_DELAYS = (7, 14, 21)
MIN_DELAY, MAX_DELAY = 1, 90


def validated_delays(raw: Sequence[int]) -> tuple[int, int, int]:
    """The delays of the three waiting follow-ups (days after the application): three strictly
    increasing integers from 1 to 90, otherwise (7, 14, 21)."""
    ok = (
        len(raw) == len(DEFAULT_DELAYS)
        and all(isinstance(n, int) and not isinstance(n, bool) for n in raw)
        and all(MIN_DELAY <= n <= MAX_DELAY for n in raw)
        and all(a < b for a, b in zip(raw, raw[1:], strict=False))
    )
    return (raw[0], raw[1], raw[2]) if ok else DEFAULT_DELAYS
