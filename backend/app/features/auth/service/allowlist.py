"""`ALLOWED_EMAILS` (P8, arbitration of phase 9): who may enter in Google mode.

Comma-separated list, compared in lowercase without spaces; `*` lets in all Google accounts.
Empty or absent: nobody gets in (and startup is refused, see `startup`). Checked at sign-in and
on each request, but read **at startup** (`Settings`): removing an address from the `.env` cuts
that account's access at the back-end restart, not before."""

ALL_ACCOUNTS = "*"


def entries(raw: str | None) -> frozenset[str]:
    """The addresses in the list, in lowercase, without spaces or empty items."""
    if raw is None:
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def allowed(email: str, raw: str | None) -> bool:
    listed = entries(raw)
    return ALL_ACCOUNTS in listed or email.strip().lower() in listed


def explicitly_allowed(email: str, raw: str | None) -> bool:
    """True if the address is **named** in a list without `*`: only a named person can be
    offered the local space (with `*`, any passer-by could take data that is not theirs)."""
    listed = entries(raw)
    return ALL_ACCOUNTS not in listed and email.strip().lower() in listed
