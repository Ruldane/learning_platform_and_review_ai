import type { BoardApi } from "./boardApi";
import { loadExcalidraw } from "./excalidrawAssets";

export type ExportFormat = "png" | "svg" | "scene";

const EXTENSIONS: Record<ExportFormat, string> = { png: "png", svg: "svg", scene: "excalidraw" };

function fileName(title: string, format: ExportFormat): string {
  const slug = title
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `tremplin-${slug || "tableau"}.${EXTENSIONS[format]}`;
}

function download(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

/** Excalidraw se charge à la demande : il pèse lourd et n'est utile qu'une fois le tableau ouvert. */
async function serialize(api: BoardApi): Promise<string> {
  const { serializeAsJSON } = await loadExcalidraw();
  return serializeAsJSON(api.getSceneElements(), api.getAppState(), api.getFiles(), "local");
}

/** La scène telle que l'enregistre Excalidraw (`.excalidraw`), en objet, fichiers compris. */
export async function serializeScene(api: BoardApi): Promise<Record<string, unknown>> {
  return JSON.parse(await serialize(api)) as Record<string, unknown>;
}

async function makeBlob(format: ExportFormat, api: BoardApi): Promise<Blob> {
  if (format === "scene") {
    return new Blob([await serialize(api)], { type: "application/vnd.excalidraw+json" });
  }
  const { exportToBlob, exportToSvg } = await loadExcalidraw();
  const elements = api.getSceneElements();
  const appState = { ...api.getAppState(), exportBackground: true };
  const files = api.getFiles();
  if (format === "png") {
    return exportToBlob({ elements, appState, files, mimeType: "image/png" });
  }
  const svg = await exportToSvg({ elements, appState, files });
  return new Blob([new XMLSerializer().serializeToString(svg)], { type: "image/svg+xml" });
}

/** Exporte le tableau affiché et déclenche le téléchargement du fichier. */
export async function exportBoard(
  format: ExportFormat,
  api: BoardApi,
  title: string,
): Promise<void> {
  download(await makeBlob(format, api), fileName(title, format));
}
