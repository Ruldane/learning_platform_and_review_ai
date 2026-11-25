import { useEffect, useRef } from "react";
import { useCaptureRequest } from "@/shared/lib/captureRequest";
import type { SocketFactory } from "@/shared/realtime/socket";
import { CaptureDialogBody } from "./CaptureDialogBody";
import { useCaptureDialog } from "./captureDialog";
import { useCaptureShortcut } from "./hooks/useCaptureShortcut";

/**
 * The `overlay` slot of the capture: listens for Ctrl+K / Cmd+K across the whole app and opens the
 * dialog when another feature asks for it (`useCaptureRequest`, when its counter changes: not
 * on mount) and mounts it while open. `createSocket` is only used in tests (fake WebSocket).
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
