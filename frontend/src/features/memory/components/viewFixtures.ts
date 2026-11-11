import type {
  DocumentRow,
  ItemFilterValue,
  MapPointView,
  MemoryItemDetailView,
  MemoryItemRow,
  MemoryStatsView,
  SearchHitView,
} from "./viewTypes";

/** Données de test des composants de l'explorateur (jamais importées par le code de production). */
export const NO_FILTERS: ItemFilterValue = { kind: "", tag: "", author: "", since: "", until: "" };

export function row(overrides: Partial<MemoryItemRow> = {}): MemoryItemRow {
  return {
    id: "a",
    kind: "acquis",
    title: "Attention",
    tags: [],
    created_by: "user",
    created_at: "2026-11-11T10:00:00Z",
    status: "active",
    indexed: true,
    level: null,
    reason: null,
    ...overrides,
  };
}

export function detail(overrides: Partial<MemoryItemDetailView> = {}): MemoryItemDetailView {
  return {
    ...row(),
    text: "Le mécanisme d'attention pondère les jetons.",
    evidence: [],
    session_id: null,
    chunks: [],
    neighbors: [],
    writes: [],
    ...overrides,
  };
}

export function hit(overrides: Partial<SearchHitView> = {}): SearchHitView {
  return {
    chunk_id: "c1",
    item_id: "a",
    kind: "document",
    title: "Cours NLP",
    text: "L'attention relie chaque jeton aux autres.",
    score: 0.834,
    created_by: "archivist",
    ...overrides,
  };
}

export function mapPoint(id: string, overrides: Partial<MapPointView> = {}): MapPointView {
  return { item_id: id, title: `Élément ${id}`, kind: "acquis", x: 0.2, y: -0.3, ...overrides };
}

export function stats(overrides: Partial<MemoryStatsView> = {}): MemoryStatsView {
  return {
    by_kind: { document: 3, acquis: 5, lecon: 2, source: 1, offre: 0, decision: 1 },
    total_items: 12,
    total_chunks: 48,
    pending_decisions: 1,
    unindexed_items: 0,
    last_write: {
      id: "w1",
      action: "create",
      author: "archivist",
      session_id: null,
      reason: null,
      created_at: "2026-11-11T10:00:00Z",
    },
    vectorize_share: 0.25,
    reindex: { status: "idle", done: 0, total: 0, error: null },
    dashboard_url: "http://localhost:6333/dashboard",
    ...overrides,
  };
}

export function documentRow(overrides: Partial<DocumentRow> = {}): DocumentRow {
  return {
    id: "d1",
    name: "cours.pdf",
    source_kind: "pdf",
    status: "indexed",
    error: null,
    learned: false,
    item_id: "i1",
    created_at: "2026-11-11T10:00:00Z",
    ...overrides,
  };
}
