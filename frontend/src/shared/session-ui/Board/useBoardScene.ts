import { useEffect, useState } from "react";
import type { BoardStateView } from "../boardTypes";
import { mermaidToScene } from "./boardScene";

export type BoardScene =
  | { status: "loading" }
  | { status: "failed" }
  | { status: "ready"; elements: unknown[]; files: unknown; animate: boolean };

/** A saved scene (January's states) is shown as is; otherwise the Mermaid is converted. */
function savedScene(scene: Record<string, unknown> | null): BoardScene | null {
  if (scene === null) return null;
  if (!Array.isArray(scene.elements)) return { status: "failed" };
  return { status: "ready", elements: scene.elements, files: scene.files ?? {}, animate: false };
}

/**
 * The scene to draw for a board state. Scribe states without a scene go through
 * `mermaidToScene` (animated); a failure gives `failed`, and the page shows the Mermaid fallback.
 */
export function useBoardScene(state: BoardStateView): BoardScene {
  const saved = savedScene(state.scene);
  const [converted, setConverted] = useState<{ key: string; scene: BoardScene } | null>(null);
  const key = `${state.id}\u0000${state.mermaid}`;

  useEffect(() => {
    if (saved !== null) return;
    let cancelled = false;
    void mermaidToScene(state.mermaid).then((result) => {
      if (cancelled) return;
      const scene: BoardScene = result.ok
        ? { status: "ready", elements: result.elements, files: result.files, animate: true }
        : { status: "failed" };
      setConverted({ key, scene });
    });
    return () => {
      cancelled = true;
    };
  }, [saved, state.mermaid, key]);

  if (saved !== null) return saved;
  return converted?.key === key ? converted.scene : { status: "loading" };
}
