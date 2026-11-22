"""Contrat et cas générés du système de planification de demandes."""

from datetime import timedelta

CHANGE_DELAY = timedelta(minutes=10)
DURATION = timedelta(minutes=30)
TITLE = "Planificateur de demandes"
ENTRY = "service.py"
SKILL = "Développement Python"
BRIEF = (
    "Livre un planificateur de demandes. La fonction planifier(demandes) renvoie "
    "les identifiants, dans l’ordre d’arrivée. Chaque demande a un id distinct "
    "et un indicateur urgente (vrai ou faux). Conserve la liste d’origine intacte."
)
CHANGE = (
    "Le client veut traiter les demandes urgentes en premier. "
    "Garde l’ordre d’arrivée à priorité égale et renvoie toujours les identifiants."
)

STARTER = '''"""Planification de demandes générées pour le Boss."""


def planifier(demandes):
    """Renvoie les identifiants dans l'ordre de traitement."""
    return [demande["id"] for demande in demandes]


if __name__ == "__main__":
    print(planifier([{"id": "D-1", "urgente": False}, {"id": "D-2", "urgente": True}]))
'''


def starter_files() -> dict[str, str]:
    guide = (
        f"# {TITLE}\n\n{BRIEF}\n\n"
        "Consulte la page Boss pour lire le changement du client et remettre les fichiers."
    )
    return {ENTRY: STARTER, "README.md": guide}
