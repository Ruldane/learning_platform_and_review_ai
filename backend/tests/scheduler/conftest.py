"""Les tâches planifiées se testent sur la production réelle des leçons : mêmes fixtures que
`tests/features/lessons` (base de test, lanceur qui écrit la session, port du programme)."""

from tests.features.lessons.conftest import (  # noqa: F401  (fixtures réutilisées)
    fake_web,
    fetcher,
    job_ctx,
    launcher,
    lessons_rt,
    program_rt,
    replan_rt,
)
