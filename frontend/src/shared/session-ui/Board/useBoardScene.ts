import { useEffect, useState } from "react";
import type { BoardStateView } from "../boardTypes";
import { mermaidToScene } from "./boardScene";

export type BoardScene =
  | { status: "loading" }
  | { status: "failed" }
  | { status: "ready"; elements: unknown[]; files: unknown; animate: boolean };

/** Une scène enregistrée (états de January) s'affiche telle quelle ; sinon on convertit le Mermaid. */
function savedScene(scene: Record<string, unknown> | null): BoardScene | null {
  if (scene === null) return null;
  if (!Array.isArray(scene.elements)) return { status: "failed" };
  return { status: "ready", elements: scene.elements, files: scene.files ?? {}, animate: false };
}

/**
 * La scène à dessiner pour un état du tableau. Les états du Scribe sans scène passent par
 * `mermaidToScene` (animés) ; un échec rend `failed` et la page affiche le repli Mermaid.
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
