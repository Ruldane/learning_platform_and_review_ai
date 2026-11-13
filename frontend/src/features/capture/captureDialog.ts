import { create } from "zustand";

interface CaptureDialogState {
  /** Le dialogue de capture est ouvert. */
  open: boolean;
  /** La session de l'Archiviste en cours (ou finie, tant qu'on ne repart pas d'une nouvelle). */
  sessionId: string | null;
  /** Le brouillon du champ lien ou note : gardé à la fermeture, vidé à l'envoi. */
  draft: string;
  /** Le brouillon du texte collé pour un lien illisible (`capture_text`). */
  textDraft: string;
  openDialog: () => void;
  closeDialog: () => void;
  /** Une capture est lancée : le dialogue la suit, le champ est vidé. */
  follow: (sessionId: string) => void;
  /** Repart d'un champ vide. */
  restart: () => void;
  setDraft: (draft: string) => void;
  setTextDraft: (textDraft: string) => void;
}

/**
 * L'état du dialogue de capture, partagé entre le raccourci, le bouton de la barre du haut et le
 * dialogue lui-même. Fermer (Échap, clic à côté) ne perd rien : ni la capture en cours, ni ce qui
 * était saisi. Un brouillon ne part qu'à l'envoi, à « Abandonner » ou à « Nouvelle capture ».
 */
export const useCaptureDialog = create<CaptureDialogState>((set) => ({
  open: false,
  sessionId: null,
  draft: "",
  textDraft: "",
  openDialog: () => set({ open: true }),
  closeDialog: () => set({ open: false }),
  follow: (sessionId) => set({ sessionId, draft: "" }),
  restart: () => set({ sessionId: null, draft: "", textDraft: "" }),
  setDraft: (draft) => set({ draft }),
  setTextDraft: (textDraft) => set({ textDraft }),
}));
