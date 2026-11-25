"""The Tutor's optional marker on the latest answer to an exercise."""

import re

from app.agents.tools.conversation_port import FocusOutcome

_MARK = re.compile(r"(?:^|\n)<!-- concentration:(correct|retry) -->\s*\Z")


def training_outcome(reply: str) -> tuple[str, FocusOutcome | None]:
    mark = _MARK.search(reply)
    if mark is None:
        return reply, None
    text = reply[: mark.start()].rstrip()
    if not text:
        return reply, None
    return text, "correct" if mark[1] == "correct" else "retry"
