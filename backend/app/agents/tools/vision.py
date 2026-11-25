"""Multimodal message for a model that reads images (`vision` level, D125): a text followed
by PNG images in base64, in the **common** form of LangChain's content blocks
(`{"type": "image", "base64": …, "mime_type": "image/png"}`, the "Messages" documentation of
LangChain 1.x, checked via context7): `ChatOpenAI` (and so GLM through `base_url`) converts it to
`image_url` `data:`, `ChatAnthropic` en bloc `image` base64.

Images of a CV are personal data: never logged."""

import base64
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import HumanMessage

MAX_IMAGES = 4  # a 4-page CV (`MAX_CV_PAGES`), or 2 original pages and 2 rendered pages
PNG_MIME = "image/png"


def image_block(png: bytes) -> dict[str, Any]:
    return {"type": "image", "base64": base64.b64encode(png).decode("ascii"), "mime_type": PNG_MIME}


def image_message(text: str, images: Sequence[bytes]) -> HumanMessage:
    """`text`, then the first `MAX_IMAGES` images of `images` (beyond: ignored; the caller
    choisit l'ordre)."""
    content: list[str | dict[str, Any]] = [{"type": "text", "text": text}]
    content += [image_block(png) for png in images[:MAX_IMAGES]]
    return HumanMessage(content=content)
