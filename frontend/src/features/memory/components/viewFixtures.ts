import type {
  ItemFilterValue,
  MemoryItemDetailView,
  MemoryItemRow,
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
