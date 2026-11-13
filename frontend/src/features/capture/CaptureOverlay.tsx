import type { SocketFactory } from "@/shared/realtime/socket";
import { CaptureDialogBody } from "./CaptureDialogBody";
import { useCaptureDialog } from "./captureDialog";
import { useCaptureShortcut } from "./hooks/useCaptureShortcut";

/**
 * L'emplacement `overlay` de la capture : écoute Ctrl+K / Cmd+K sur toute l'application et monte le
 * dialogue quand il est ouvert. `createSocket` ne sert qu'aux tests (faux WebSocket).
 */
export function CaptureOverlay({ createSocket }: { createSocket?: SocketFactory }) {
  const open = useCaptureDialog((state) => state.open);
  const openDialog = useCaptureDialog((state) => state.openDialog);
  useCaptureShortcut(openDialog);
  return open ? <CaptureDialogBody createSocket={createSocket} /> : null;
}
