declare global {
  interface Window {
    EXCALIDRAW_ASSET_PATH?: string | string[];
  }
}

// Excalidraw reads `window.EXCALIDRAW_ASSET_PATH` as soon as it is evaluated to find fonts: they
// are served by the front end (see `vite.excalidraw-fonts.ts`), not by a CDN. This module therefore
// sets the path when it is evaluated; any file importing Excalidraw imports this module first.
window.EXCALIDRAW_ASSET_PATH = `${import.meta.env.BASE_URL}excalidraw-assets/`;

/** Loads Excalidraw on demand, once its font path is set. */
export function loadExcalidraw() {
  return import("@excalidraw/excalidraw");
}
