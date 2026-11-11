import { MEMORY_KINDS } from "./components/kindColors";
import type {
  DocumentOut,
  DocumentRow,
  MapPointView,
  MapResponse,
  MemoryItemDetail,
  MemoryItemDetailView,
  MemoryItemOut,
  MemoryItemRow,
  MemoryKindView,
  MemoryStatsView,
  MemoryWriteOut,
  SearchHitOut,
  SearchHitView,
  StatsOut,
} from "./types";

/** Ligne de la liste : pas de texte, il se lit dans le détail. */
export function toItemRow(item: MemoryItemOut): MemoryItemRow {
  return {
    id: item.id,
    kind: item.kind,
    title: item.title,
    tags: item.tags,
    created_by: item.created_by,
    created_at: item.created_at,
    status: item.status,
    indexed: item.indexed,
    level: item.level,
    reason: item.reason,
  };
}

function toWrite(write: MemoryWriteOut) {
  return {
    id: write.id,
    action: write.action,
    author: write.author,
    session_id: write.session_id,
    reason: write.reason,
    created_at: write.created_at,
  };
}

/** Détail d'un élément : texte, preuves, fragments, voisins et journal des écritures. */
export function toItemDetail(item: MemoryItemDetail): MemoryItemDetailView {
  return {
    ...toItemRow(item),
    text: item.text,
    evidence: item.evidence,
    session_id: item.session_id,
    chunks: item.chunks.map(({ id, ordinal, text, token_count }) => ({
      id,
      ordinal,
      text,
      token_count,
    })),
    neighbors: item.neighbors.map(({ item_id, title, kind, score }) => ({
      item_id,
      title,
      kind,
      score,
    })),
    writes: item.writes.map(toWrite),
  };
}

/** Le contrat type `by_kind` en dictionnaire ouvert : on le replie sur les six types connus. */
function toByKind(raw: Record<string, number>): Record<MemoryKindView, number> {
  const counts = {} as Record<MemoryKindView, number>;
  for (const kind of MEMORY_KINDS) {
    const count = raw[kind];
    counts[kind] = typeof count === "number" && Number.isFinite(count) ? count : 0;
  }
  return counts;
}

/** Statistiques : six types toujours présents (0 par défaut), sans les champs que l'écran n'affiche pas. */
export function toStats(stats: StatsOut): MemoryStatsView {
  return {
    by_kind: toByKind(stats.by_kind),
    total_items: stats.total_items,
    total_chunks: stats.total_chunks,
    pending_decisions: stats.pending_decisions,
    unindexed_items: stats.unindexed_items,
    last_write: stats.last_write ? toWrite(stats.last_write) : null,
    vectorize_share: stats.vectorize_share,
    reindex: {
      status: stats.reindex.status,
      done: stats.reindex.done,
      total: stats.reindex.total,
      error: stats.reindex.error,
    },
    dashboard_url: stats.dashboard_url,
  };
}

export function toHit(hit: SearchHitOut): SearchHitView {
  return {
    chunk_id: hit.chunk_id,
    item_id: hit.item_id,
    kind: hit.kind,
    title: hit.title,
    text: hit.text,
    score: hit.score,
    created_by: hit.created_by,
  };
}

export function toMapPoints(map: MapResponse): MapPointView[] {
  return map.points.map(({ item_id, title, kind, x, y }) => ({ item_id, title, kind, x, y }));
}

/** Ligne de la liste des documents ; l'adresse d'un lien et la taille ne sortent pas du back. */
export function toDocumentRow(document: DocumentOut): DocumentRow {
  return {
    id: document.id,
    name: document.name,
    source_kind: document.source_kind,
    status: document.status,
    error: document.error ? { code: document.error.code, message: document.error.message } : null,
    learned: document.learned,
    item_id: document.item_id,
    created_at: document.created_at,
  };
}
