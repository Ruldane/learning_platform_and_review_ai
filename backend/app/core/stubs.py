"""Stub of a route placed by a phase's contract before its implementation: 501
`not_implemented`. Each flow replaces the body of its routes; the phase's contract test
lists those that are still stubs."""

from typing import NoReturn

from app.core.errors import AppError


def not_implemented() -> NoReturn:
    raise AppError("not_implemented", "Not available yet.", 501)
