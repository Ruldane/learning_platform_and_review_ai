import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { startCapture, uploadFile } from "../api";
import type { CaptureSource } from "../components/viewTypes";
import { captureErrorMessage } from "../errors";

export type CaptureInput = CaptureSource | { kind: "file"; file: File };

/** Le départ d'une capture : un lien, une note, ou un fichier importé puis capturé par son document. */
async function launch(input: CaptureInput, onUpload: (uploading: boolean) => void) {
  if (input.kind === "url") return startCapture({ url: input.url });
  if (input.kind === "text") return startCapture({ text: input.text });
  onUpload(true);
  try {
    const document = await uploadFile(input.file);
    return await startCapture({ document_id: document.id });
  } finally {
    onUpload(false);
  }
}

/**
 * Lance une capture par `POST /capture` (jamais `POST /sessions`) et rend l'identifiant de session
 * à `onSession`. Un fichier passe d'abord par `POST /documents`. Un refus s'affiche sous le champ,
 * dans un texte clair ; un seul départ à la fois (verrou posé de façon synchrone).
 */
export function useStartCapture(onSession: (sessionId: string) => void) {
  const sending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const mutation = useMutation({
    mutationFn: (input: CaptureInput) => launch(input, setUploading),
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
  return { start, pending: mutation.isPending, uploading, error };
}
