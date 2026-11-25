import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { startCapture, uploadFile } from "../api";
import type { CaptureSource } from "../components/viewTypes";
import { captureErrorMessage } from "../errors";

export type CaptureInput = CaptureSource | { kind: "file"; file: File };

/** Starting a capture: a link, a note, or a file imported then captured by its document. */
async function launch(
  input: CaptureInput,
  onUpload: (uploading: boolean) => void,
  source?: RunSource,
) {
  if (input.kind === "url") return startCapture({ url: input.url }, source);
  if (input.kind === "text") return startCapture({ text: input.text }, source);
  onUpload(true);
  try {
    const document = await uploadFile(input.file);
    return await startCapture({ document_id: document.id }, source);
  } finally {
    onUpload(false);
  }
}

/**
 * Starts a capture with `POST /capture` (never `POST /sessions`) and returns the session id
 * to `onSession`. A file goes through `POST /documents` first. A refusal is shown below the field,
 * in plain text; only one start at a time (a lock set synchronously).
 */
export function useStartCapture(onSession: (sessionId: string) => void) {
  const provider = useLaunchSource();
  const sending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const mutation = useMutation({
    mutationFn: (input: CaptureInput) => launch(input, setUploading, provider.source),
  });
  const { mutateAsync } = mutation;

  const start = async (input: CaptureInput): Promise<void> => {
    if (sending.current) return;
    sending.current = true;
    setError(null);
    try {
      onSession((await mutateAsync(input)).session_id);
    } catch (failure) {
      setError(captureErrorMessage(failure));
    }
    sending.current = false;
  };
  return { start, pending: mutation.isPending, uploading, error, launchMenu: provider.menu };
}
