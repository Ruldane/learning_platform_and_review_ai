import { create } from "zustand";
import { onLocalReset } from "@/shared/lib/localReset";

interface CaptureDialogState {
  /** The capture dialog is open. */
  open: boolean;
  /** The Archivist session in progress (or finished, until a new one starts). */
  sessionId: string | null;
  /** The draft of the link or note field: kept on close, cleared on send. */
  draft: string;
  /** The draft of the pasted text for an unreadable link (`capture_text`). */
  textDraft: string;
  openDialog: () => void;
  closeDialog: () => void;
  /** A capture is started: the dialog follows it and the field is cleared. */
  follow: (sessionId: string) => void;
  /** Starts again from an empty field. */
  restart: () => void;
  setDraft: (draft: string) => void;
  setTextDraft: (textDraft: string) => void;
}

/**
 * The state of the capture dialog, shared by the shortcut, the top bar button and the
 * dialog itself. Closing (Escape, click outside) loses nothing: not the running capture,
 * nor what was typed. A draft is only dropped on send, « Abandonner » or « Nouvelle capture ».
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

// « Tout supprimer »: no running capture or draft from the cleared space stays in the dialog.
onLocalReset(() => useCaptureDialog.getState().restart());
