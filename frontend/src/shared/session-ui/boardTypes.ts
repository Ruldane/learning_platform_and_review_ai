/** View types for the board: local, with no link to `shared/api` (D34). */
export type BoardKind =
  "domain_map" | "prerequisites" | "timeline" | "comparison" | "lesson" | "system_design";

export interface BoardStateView {
  id: string;
  kind: BoardKind;
  title: string;
  step: number;
  /** The Mermaid `flowchart` written by the Scribe; never coordinates. */
  mermaid: string;
  /** Saved Excalidraw scene (January's states); `null` while the front end still has to convert. */
  scene: Record<string, unknown> | null;
  author: "scribe" | "tutor" | "user";
  createdAt: string;
}

/**
 * Board texts specific to the page showing it (the Tutor also draws, not only the
 * Scribe); when absent, the Council's.
 */
export interface BoardLabels {
  label: string;
  empty: string;
  drawing: string;
  save?: string;
}

/** January's changes: the full scene and the note summarizing them for the agents. */
export interface BoardEdit {
  scene: Record<string, unknown>;
  note: string;
}

/** What `annotationNote` reads of an Excalidraw element (a subset, to avoid the package). */
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
