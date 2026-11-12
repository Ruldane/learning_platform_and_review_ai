declare global {
  interface Window {
    EXCALIDRAW_ASSET_PATH?: string | string[];
  }
}

// Excalidraw lit `window.EXCALIDRAW_ASSET_PATH` dès qu'il est évalué pour trouver ses polices : elles
// sont servies par le front (voir `vite.excalidraw-fonts.ts`), pas par un CDN. Ce module fixe donc
// le chemin à son évaluation ; tout fichier qui importe Excalidraw importe d'abord ce module.
window.EXCALIDRAW_ASSET_PATH = `${import.meta.env.BASE_URL}excalidraw-assets/`;

/** Charge Excalidraw à la demande, une fois le chemin de ses polices fixé. */
export function loadExcalidraw() {
  return import("@excalidraw/excalidraw");
}
