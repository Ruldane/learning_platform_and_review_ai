"""Composition de l'IDE Python (phase 10) : le bac à sable (`CodeSandbox`), l'exécuteur des
exécutions et le professeur. Vide pour l'instant : 10.A1 y branche le bac (`spool`, ou
`FakeSandbox` en test) et 10.A3 le professeur. Comme `app.bootstrap`, seul `app.main` l'importe,
par `app.bootstrap` (contrat 5)."""

from fastapi import FastAPI


def compose_ide(app: FastAPI) -> None:
    """Pose sur `app.state` ce que les routes de l'IDE lisent. Rien avant 10.A1."""
