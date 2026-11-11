/**
 * Types de vue des composants de l'explorateur de mémoire : miroir structurel des schémas de
 * l'API, mais locaux (les composants présentationnels n'importent jamais `shared/api`).
 */
export type MemoryKindView = "document" | "acquis" | "lecon" | "source" | "offre" | "decision";
export type MasteryLevelView = "declare" | "en_cours" | "valide" | "prouve";
export type WriteActionView = "create" | "update" | "delete" | "confirm" | "reject" | "merge";

export interface MemoryItemRow {
  id: string;
  kind: MemoryKindView;
  title: string;
  tags: string[];
  created_by: string;
  created_at: string;
  status: "active" | "pending";
  indexed: boolean;
  level: MasteryLevelView | null;
  reason: string | null;
}

export interface MemoryWriteView {
  id: string;
  action: WriteActionView;
  author: string;
  session_id: string | null;
  reason: string | null;
  created_at: string;
}

export interface MemoryItemDetailView extends MemoryItemRow {
  text: string;
  evidence: string[];
  session_id: string | null;
  chunks: { id: string; ordinal: number; text: string; token_count: number }[];
  neighbors: { item_id: string; title: string; kind: MemoryKindView; score: number }[];
  writes: MemoryWriteView[];
}

export interface SearchHitView {
  chunk_id: string;
  item_id: string;
  kind: MemoryKindView;
  title: string;
  text: string;
  score: number;
  created_by: string;
}

export interface ItemFilterValue {
  kind: MemoryKindView | "";
  tag: string;
  author: string;
  since: string;
  until: string;
}

export interface ItemEdit {
  title: string;
  text: string;
  tags: string[];
  level: "declare" | "en_cours" | null;
}

export interface NewItem extends ItemEdit {
  kind: "acquis" | "decision" | "offre";
}
