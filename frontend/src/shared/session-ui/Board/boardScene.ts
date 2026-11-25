import { loadExcalidraw } from "./excalidrawAssets";

export type SceneResult =
  { ok: true; elements: unknown[]; files: unknown } | { ok: false; error: string };

// A Scribe diagram has a few dozen nodes at most: beyond that, the fallback is better.
const LIMITS = { maxEdges: 300, maxTextSize: 20_000 };

/**
 * Converts the Scribe's Mermaid `flowchart` into Excalidraw elements. Both packages are loaded
 * on demand (they are heavy). The error rendered never contains the code: a parser message
 * may quote it, and the code is not logged (SPEC 17.4).
 */
export async function mermaidToScene(mermaid: string): Promise<SceneResult> {
  try {
    const [{ parseMermaidToExcalidraw }, { convertToExcalidrawElements }] = await Promise.all([
      import("@excalidraw/mermaid-to-excalidraw"),
      loadExcalidraw(),
    ]);
    const parsed = await parseMermaidToExcalidraw(mermaid, LIMITS);
    const elements = convertToExcalidrawElements(parsed.elements, { regenerateIds: false });
    if (elements.length === 0) return { ok: false, error: "empty_scene" };
    return { ok: true, elements, files: parsed.files ?? {} };
  } catch {
    return { ok: false, error: "conversion_failed" };
  }
}
