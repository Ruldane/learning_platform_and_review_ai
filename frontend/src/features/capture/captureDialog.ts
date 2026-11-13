import { create } from "zustand";

interface CaptureDialogState {
  /** Le dialogue de capture est ouvert. */
  open: boolean;
  /** La session de l'Archiviste en cours (ou finie, tant qu'on ne repart pas d'une nouvelle). */
  sessionId: string | null;
  openDialog: () => void;
  closeDialog: () => void;
  /** Une capture est lancée : le dialogue la suit. */
  follow: (sessionId: string) => void;
  /** Repart d'un champ vide. */
  restart: () => void;
}

/**
 * L'état du dialogue de capture, partagé entre le raccourci, le bouton de la barre du haut et le
 * dialogue lui-même. Fermer ne perd pas la capture en cours : la rouvrir la retrouve.
 */
export const useCaptureDialog = create<CaptureDialogState>((set) => ({
  open: false,
  sessionId: null,
  openDialog: () => set({ open: true }),
  closeDialog: () => set({ open: false }),
  follow: (sessionId) => set({ sessionId }),
  restart: () => set({ sessionId: null }),
}));
