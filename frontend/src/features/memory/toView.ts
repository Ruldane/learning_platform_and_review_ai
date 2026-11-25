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

/** List row: no text, it is read in the detail. */
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

/** Item detail: text, evidence, fragments, neighbours and write log. */
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
    linkedNotes: (item.linked_notes ?? []).map(({ item_id, title }) => ({ itemId: item_id, title })),
    writes: item.writes.map(toWrite),
  };
}

/** The `by_kind` contract type as an open dictionary: it is folded onto the six known types. */
function toByKind(raw: Record<string, number>): Record<MemoryKindView, number> {
  const counts = {} as Record<MemoryKindView, number>;
  for (const kind of MEMORY_KINDS) {
    const count = raw[kind];
    counts[kind] = typeof count === "number" && Number.isFinite(count) ? count : 0;
  }
  return counts;
}

/** Statistics: the six types always present (0 by default); fields the screen hides are dropped. */
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

/** Document list row; a link's address and the size do not come from the back end. */
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
