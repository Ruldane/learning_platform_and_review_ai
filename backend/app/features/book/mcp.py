from app.mcp.base import FeatureMcp, McpAction

_BOOK = "/programs/{program_id}/book"

MCP = FeatureMcp(
    feature="book",
    actions=(
        McpAction(
            f"GET {_BOOK}", 1, "book_get_book", "État de l’édition PDF et EPUB du programme."
        ),
        McpAction(
            f"POST {_BOOK}",
            3,
            "book_request_book",
            "Prépare une édition du programme en arrière-plan. Produit deux fichiers, à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "GET /programs/{program_id}/book/{format}",
            1,
            "book_get_edition_file",
            "Lit les métadonnées du livre et donne son lien local.",
            artifact=True,
        ),
    ),
)
