import { useEffect, useRef } from "react";
import { useCaptureRequest } from "@/shared/lib/captureRequest";
import type { SocketFactory } from "@/shared/realtime/socket";
import { CaptureDialogBody } from "./CaptureDialogBody";
import { useCaptureDialog } from "./captureDialog";
import { useCaptureShortcut } from "./hooks/useCaptureShortcut";

/**
 * L'emplacement `overlay` de la capture : écoute Ctrl+K / Cmd+K sur toute l'application, ouvre le
 * dialogue à la demande d'une autre feature (`useCaptureRequest`, quand son compteur change : pas
 * au montage) et le monte quand il est ouvert. `createSocket` ne sert qu'aux tests (faux WebSocket).
 */
export function CaptureOverlay({ createSocket }: { createSocket?: SocketFactory }) {
  const open = useCaptureDialog((state) => state.open);
  const openDialog = useCaptureDialog((state) => state.openDialog);
  const requests = useCaptureRequest((state) => state.count);
  const seen = useRef(requests);
  useCaptureShortcut(openDialog);
  useEffect(() => {
    if (requests === seen.current) return;
    seen.current = requests;
    openDialog();
  }, [requests, openDialog]);
  return open ? <CaptureDialogBody createSocket={createSocket} /> : null;
}
