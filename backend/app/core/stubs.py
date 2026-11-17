"""Bouchon d'une route posée par le contrat d'une phase avant son implémentation : 501
`not_implemented`. Chaque flux remplace le corps de ses routes ; le test de contrat de la phase
liste celles qui restent des bouchons."""

from typing import NoReturn

from app.core.errors import AppError


def not_implemented() -> NoReturn:
    raise AppError("not_implemented", "Pas encore disponible.", 501)
