"""Services de la connexion, de la disponibilité et des confirmations Agenda."""

from app.features.calendar.service.oauth import status as connection_status

__all__ = ["connection_status"]
