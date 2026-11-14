"""Message multimodal pour un modèle qui lit les images (niveau `vision`, D125) : un texte suivi
d'images PNG en base64, sous la forme **commune** des blocs de contenu de LangChain
(`{"type": "image", "base64": …, "mime_type": "image/png"}`, documentation « Messages » de
LangChain 1.x, vérifiée par context7) : `ChatOpenAI` (et donc GLM par `base_url`) la convertit en
`image_url` `data:`, `ChatAnthropic` en bloc `image` base64.

Les images d'un CV sont des données personnelles : jamais journalisées."""

import base64
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import HumanMessage

MAX_IMAGES = 4  # un CV de 4 pages (`MAX_CV_PAGES`), ou 2 pages d'origine et 2 pages du rendu
PNG_MIME = "image/png"


def image_block(png: bytes) -> dict[str, Any]:
    return {"type": "image", "base64": base64.b64encode(png).decode("ascii"), "mime_type": PNG_MIME}


def image_message(text: str, images: Sequence[bytes]) -> HumanMessage:
    """`text`, puis les `MAX_IMAGES` premières images de `images` (au-delà : ignorées ; l'appelant
    choisit l'ordre)."""
    content: list[str | dict[str, Any]] = [{"type": "text", "text": text}]
    content += [image_block(png) for png in images[:MAX_IMAGES]]
    return HumanMessage(content=content)
