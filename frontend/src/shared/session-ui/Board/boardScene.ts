import { loadExcalidraw } from "./excalidrawAssets";

export type SceneResult =
  { ok: true; elements: unknown[]; files: unknown } | { ok: false; error: string };

// Un schéma du Scribe tient en quelques dizaines de nœuds : au-delà, mieux vaut le repli.
const LIMITS = { maxEdges: 300, maxTextSize: 20_000 };

/**
 * Convertit le `flowchart` Mermaid du Scribe en éléments Excalidraw. Les deux paquets sont chargés
 * à la demande (ils pèsent lourd). L'erreur rendue ne contient jamais le code : un message de
 * l'analyseur peut le citer, et le code ne se journalise pas (SPEC 17.4).
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
