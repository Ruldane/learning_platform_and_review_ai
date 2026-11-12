import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";

/** Ce que le tableau utilise de l'API impérative d'Excalidraw (types seulement : rien à charger). */
export type BoardApi = Pick<
  ExcalidrawImperativeAPI,
  "getSceneElements" | "getAppState" | "getFiles" | "updateScene" | "addFiles" | "scrollToContent"
>;
