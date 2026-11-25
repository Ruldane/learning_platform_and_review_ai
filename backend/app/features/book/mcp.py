from app.mcp.base import FeatureMcp, McpAction

_BOOK = "/programs/{program_id}/book"

MCP = FeatureMcp(
    feature="book",
    actions=(
        McpAction(
            f"GET {_BOOK}", 1, "book_get_book", "State of the program's PDF and EPUB edition."
        ),
        McpAction(
            f"POST {_BOOK}",
            3,
            "book_request_book",
            "Prepares an edition of the program in the background. Produces two files; asks "
            "for confirmation.",
            side_effects="external",
        ),
        McpAction(
            "GET /programs/{program_id}/book/{format}",
            1,
            "book_get_edition_file",
            "Reads the book's metadata and gives its local link.",
            artifact=True,
        ),
    ),
)
