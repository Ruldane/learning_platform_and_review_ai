"""`ALLOWED_EMAILS` (P8, arbitrage de la phase 9) : qui a le droit d'entrer en mode Google.

Liste séparée par des virgules, comparée en minuscules sans espaces ; `*` laisse entrer tous les
comptes Google. Vide ou absente : personne n'entre (et le démarrage est refusé, voir `startup`).
Contrôlée à la connexion et à chaque requête : retirer une adresse coupe l'accès aussitôt."""

ALL_ACCOUNTS = "*"


def entries(raw: str | None) -> frozenset[str]:
    """Les adresses de la liste, en minuscules, sans espaces ni éléments vides."""
    if raw is None:
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def allowed(email: str, raw: str | None) -> bool:
    listed = entries(raw)
    return ALL_ACCOUNTS in listed or email.strip().lower() in listed
