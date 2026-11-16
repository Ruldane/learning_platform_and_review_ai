import { create } from "zustand";

interface CaptureRequestState {
  /** Nombre de demandes d'ouverture de la capture depuis le démarrage de l'application. */
  count: number;
  /** Demande l'ouverture de la capture ; la feature `capture` l'écoute, aucune autre n'en dépend. */
  request: () => void;
}

/**
 * Le magasin partagé « ouvre la capture » : une feature qui veut offrir l'action (l'accueil) appelle
 * `request()` sans importer `capture` ; `CaptureOverlay` ouvre son dialogue quand `count` change
 * (jamais au montage : un compteur déjà levé n'est pas une demande).
 */
export const useCaptureRequest = create<CaptureRequestState>((set) => ({
  count: 0,
  request: () => set((state) => ({ count: state.count + 1 })),
}));
