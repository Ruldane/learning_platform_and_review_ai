"""Déclaration MCP de `memory` : éléments, recherche, documents collés, carte et export.

Écrire un élément l'indexe dans Qdrant (vecteurs) : l'annulation ne couvre que la base, donc ces
écritures sont déclarées `external` et de niveau 3."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_ITEM = ("title", "text")

MCP = FeatureMcp(
    feature="memory",
    actions=(
        McpAction(
            "GET /memory/items",
            1,
            "memory_list_items",
            "Les éléments de la mémoire, filtrables (type, étiquette, auteur, dates, statut).",
            untrusted=("items[].title", "items[].text"),
        ),
        McpAction(
            "GET /memory/items/{item_id}",
            1,
            "memory_get_item",
            "Un élément de la mémoire : fragments, voisins et journal d'écriture.",
            untrusted=("title", "text", "chunks[].text"),
        ),
        McpAction(
            "POST /memory/search",
            1,
            "memory_search_items",
            "Recherche sémantique dans la mémoire (ne change rien).",
            untrusted=("hits[].title", "hits[].text", "agent_text"),
        ),
        McpAction("GET /memory/map", 1, "memory_get_map", "La carte 2D de la mémoire."),
        McpAction("GET /memory/stats", 1, "memory_get_stats", "Statistiques de la mémoire."),
        McpAction(
            "GET /memory/export",
            1,
            "memory_export_memory",
            "Toute la mémoire en JSON, sans vecteurs.",
            untrusted=("items[].title", "items[].text", "documents[].name", "documents[].url"),
        ),
        McpAction(
            "GET /documents",
            1,
            "memory_list_documents",
            "Les 200 documents importés les plus récents.",
            untrusted=("[].name", "[].url"),
        ),
        McpAction(
            "POST /memory/items",
            3,
            "memory_create_item",
            "Écrit un élément en mémoire (note, fait, décision…) et l'indexe : demande à "
            "confirmer, car les vecteurs ne s'annulent pas.",
            side_effects="external",
            untrusted=_ITEM,
        ),
        McpAction(
            "PATCH /memory/items/{item_id}",
            3,
            "memory_update_item",
            "Modifie un élément de la mémoire et le réindexe : demande à confirmer.",
            side_effects="external",
            untrusted=_ITEM,
        ),
        McpAction(
            "DELETE /memory/items/{item_id}",
            3,
            "memory_delete_item",
            "Supprime un élément de la mémoire, ses vecteurs et ses fichiers : demande à "
            "confirmer.",
            side_effects="external",
        ),
        McpAction(
            "POST /memory/items/{item_id}/merge",
            3,
            "memory_merge_items",
            "Fond d'autres éléments du même type dans celui-ci et le réindexe : demande à "
            "confirmer.",
            side_effects="external",
            untrusted=_ITEM,
        ),
        McpAction(
            "POST /memory/reindex",
            3,
            "memory_reindex_memory",
            "Met la réindexation de la mémoire en file : demande à confirmer (vecteurs).",
            side_effects="external",
        ),
        McpAction(
            "POST /documents/text",
            3,
            "memory_add_text_document",
            "Importe un texte collé (titre et texte) comme document : il est analysé puis "
            "indexé. Demande à confirmer (fichier et vecteurs).",
            side_effects="external",
            untrusted=("document.name", "document.url"),
        ),
        McpAction(
            "POST /documents/{document_id}/learned",
            2,
            "memory_mark_document_learned",
            "« Déjà appris » : l'Archiviste crée des acquis déclarés à partir du document.",
        ),
    ),
    graphs=(
        McpGraph(
            "learned_document",
            summary="L'Archiviste lit un document indexé (`document_id`) et crée ses acquis.",
        ),
    ),
    excluded={
        "POST /documents": (
            "Téléversement d'un fichier (multipart, `UploadFile`) : le MCP n'envoie pas de "
            "fichier ; la variante texte `POST /documents/text` le remplace."
        ),
    },
)
