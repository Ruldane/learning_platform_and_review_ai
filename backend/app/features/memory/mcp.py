"""MCP declaration for `memory`: items, search, pasted documents, map and export.

Writing an item indexes it in Qdrant (vectors): the undo only covers the database, so these
writes are declared `external` and level 3."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_ITEM = ("title", "text")

MCP = FeatureMcp(
    feature="memory",
    actions=(
        McpAction(
            "GET /memory/items",
            1,
            "memory_list_items",
            "Memory items, filterable (type, tag, author, dates, status).",
            untrusted=("items[].title", "items[].text"),
        ),
        McpAction(
            "GET /memory/items/{item_id}",
            1,
            "memory_get_item",
            "A memory item: chunks, neighbors, links and write log.",
            untrusted=("title", "text", "chunks[].text", "linked_notes[].title"),
        ),
        McpAction(
            "POST /memory/search",
            1,
            "memory_search_items",
            "Semantic search in memory (changes nothing).",
            untrusted=("hits[].title", "hits[].text", "agent_text"),
        ),
        McpAction("GET /memory/map", 1, "memory_get_map", "The 2D map of memory."),
        McpAction("GET /memory/stats", 1, "memory_get_stats", "Returns the memory statistics."),
        McpAction(
            "GET /memory/export",
            1,
            "memory_export_memory",
            "The whole memory as JSON, without vectors.",
            untrusted=("items[].title", "items[].text", "documents[].name", "documents[].url"),
        ),
        McpAction(
            "GET /documents",
            1,
            "memory_list_documents",
            "The 200 most recently imported documents.",
            untrusted=("[].name", "[].url"),
        ),
        McpAction(
            "POST /memory/items",
            3,
            "memory_create_item",
            "Writes a memory item (note, fact, decision…) and indexes it: needs confirmation, "
            "because vectors cannot be undone.",
            side_effects="external",
            untrusted=_ITEM,
        ),
        McpAction(
            "PATCH /memory/items/{item_id}",
            3,
            "memory_update_item",
            "Edits a memory item and reindexes it: needs confirmation.",
            side_effects="external",
            untrusted=_ITEM,
        ),
        McpAction(
            "DELETE /memory/items/{item_id}",
            3,
            "memory_delete_item",
            "Deletes a memory item, its vectors and its files: needs confirmation.",
            side_effects="external",
        ),
        McpAction(
            "POST /memory/items/{item_id}/merge",
            3,
            "memory_merge_items",
            "Merges other items of the same type into this one and reindexes it: needs "
            "confirmation.",
            side_effects="external",
            untrusted=_ITEM,
        ),
        McpAction(
            "POST /memory/reindex",
            3,
            "memory_reindex_memory",
            "Queues a reindexing of memory: needs confirmation (vectors).",
            side_effects="external",
        ),
        McpAction(
            "POST /documents/text",
            3,
            "memory_add_text_document",
            "Imports a pasted text (title and text) as a document: it is analyzed then "
            "indexed. Needs confirmation (file and vectors).",
            side_effects="external",
            untrusted=("document.name", "document.url"),
        ),
        McpAction(
            "POST /documents/{document_id}/learned",
            2,
            "memory_mark_document_learned",
            '"Already learned": the Archivist creates declared skills from the document.',
            launches="learned_document",
        ),
        McpAction(
            "POST /documents",
            3,
            "memory_add_link_document",
            "Imports a link as a document. Needs confirmation before analysis and indexing.",
            encoding="form",
            body_fields=frozenset({"url"}),
            side_effects="external",
            untrusted=("document.name", "document.url"),
        ),
    ),
    graphs=(
        McpGraph(
            "learned_document",
            summary="The Archivist reads an indexed document (`document_id`) and creates skills.",
        ),
    ),
)
