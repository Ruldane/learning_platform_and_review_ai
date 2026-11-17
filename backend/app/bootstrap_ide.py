"""Composition de l'IDE Python (phase 10) : le bac à sable (`CodeSandbox`), l'exécuteur des
exécutions et le professeur. 10.A1 y branche le bac (`SpoolSandbox` sur le volume d'échange, ou
`FakeSandbox` en test, posé avant par le test) ; 10.A3 y compose le port des agents (professeur,
exercices générés : `AgentIdeStore`, lu par `app.main` dans `app.state.ide_store`). Comme
`app.bootstrap`, seul `app.main` l'importe, par `app.bootstrap` (contrat 5)."""

from fastapi import FastAPI

from app.core.providers import Providers
from app.features.health.checks import SandboxCheck
from app.features.ide.service.agent_store import AgentIdeStore
from app.providers.sandbox.spool import SpoolSandbox


def compose_ide(app: FastAPI) -> None:
    """Pose le bac à sable sur `app.state.providers.sandbox` et son contrôle dans la santé
    (« Bac à sable »), puis le port de l'IDE des agents. Un bac déjà posé (test) est gardé."""
    providers: Providers = app.state.providers
    if providers.sandbox is None:
        providers.sandbox = SpoolSandbox(app.state.settings.sandbox_spool_dir)
    providers.health_checks.append(SandboxCheck(providers.sandbox))
    app.state.ide_store = AgentIdeStore(app.state.session_factory, providers)
