"""Message multimodal du Maquettiste (D125) : texte puis blocs d'image PNG en base64, forme
commune de LangChain ; `MAX_IMAGES` au plus."""

import base64

from app.agents.tools.vision import MAX_IMAGES, image_message


def test_text_then_png_blocks_in_base64() -> None:
    message = image_message("Décris ce CV.", [b"\x89PNG-1", b"\x89PNG-2"])
    assert message.content == [
        {"type": "text", "text": "Décris ce CV."},
        {
            "type": "image",
            "base64": base64.b64encode(b"\x89PNG-1").decode(),
            "mime_type": "image/png",
        },
        {
            "type": "image",
            "base64": base64.b64encode(b"\x89PNG-2").decode(),
            "mime_type": "image/png",
        },
    ]


def test_at_most_max_images_first_kept() -> None:
    pngs = [f"page-{n}".encode() for n in range(MAX_IMAGES + 2)]
    message = image_message("x", pngs)
    blocks = [b for b in message.content if isinstance(b, dict) and b["type"] == "image"]
    assert MAX_IMAGES == 4 and len(blocks) == MAX_IMAGES
    assert [base64.b64decode(b["base64"]) for b in blocks] == pngs[:MAX_IMAGES]


def test_without_images_only_text() -> None:
    assert image_message("seul", []).content == [{"type": "text", "text": "seul"}]
