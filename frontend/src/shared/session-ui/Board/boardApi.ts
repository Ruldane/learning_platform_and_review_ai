import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";

/** What the board uses of Excalidraw's imperative API (types only: nothing to load). */
export type BoardApi = Pick<
  ExcalidrawImperativeAPI,
  "getSceneElements" | "getAppState" | "getFiles" | "updateScene" | "addFiles" | "scrollToContent"
>;
