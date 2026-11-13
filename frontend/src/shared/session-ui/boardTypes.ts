/** Types de vue du tableau : locaux, sans lien avec `shared/api` (D34). */
export type BoardKind = "domain_map" | "prerequisites" | "timeline" | "comparison" | "lesson";

export interface BoardStateView {
  id: string;
  kind: BoardKind;
  title: string;
  step: number;
  /** Le `flowchart` Mermaid écrit par le Scribe ; jamais de coordonnées. */
  mermaid: string;
  /** Scène Excalidraw enregistrée (états de January) ; `null` tant que le front doit convertir. */
  scene: Record<string, unknown> | null;
  author: "scribe" | "tutor" | "user";
  createdAt: string;
}

/**
 * Textes du tableau propres à la page qui l'affiche (le Tuteur dessine aussi, pas seulement le
 * Scribe) ; absents, ceux du Conseil.
 */
export interface BoardLabels {
  label: string;
  empty: string;
  drawing: string;
}

/** Les modifications de January : la scène complète et la note qui les résume pour les agents. */
export interface BoardEdit {
  scene: Record<string, unknown>;
  note: string;
}

/** Ce que `annotationNote` lit d'un élément Excalidraw (sous-ensemble, sans dépendre du paquet). */
export interface SceneElementLike {
  id: string;
  type: string;
  x: number;
  y: number;
  text?: string;
  isDeleted?: boolean;
  containerId?: string | null;
  version?: number;
}
