"""State of the `application_kit` flow (D142). The record, its posting and the profile are in the
database (`KitStore` port): each node rereads the context through `context` (read-only); the state
only keeps the record id, the kept pieces (edited by January, never redone) and each piece's
outcome, which the parallel branches write without clashing (`outcomes`, dict merge)."""

import operator
from typing import Annotated, TypedDict


class ApplicationKitState(TypedDict, total=False):
    application_id: str
    keep: list[str]  # pieces from `KitContext.keep`, not regenerated
    outcomes: Annotated[dict[str, str], operator.or_]  # piece -> stored status
    summary: str
