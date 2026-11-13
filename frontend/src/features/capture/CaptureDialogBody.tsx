import type { SocketFactory } from "@/shared/realtime/socket";
import { useCaptureDialog } from "./captureDialog";
import { CaptureInput, CommandCapture } from "./components/CommandCapture";
import { CaptureRun } from "./CaptureRun";
import { useStartCapture } from "./hooks/useStartCapture";

/**
 * Le dialogue ouvert : le champ de capture, ou le suivi de la capture lancée. Monté seulement
 * quand le dialogue s'ouvre : tant qu'il est fermé, aucune lecture ni aucun fournisseur de données
 * n'est nécessaire (le raccourci vit dans `CaptureOverlay`).
 */
export function CaptureDialogBody({ createSocket }: { createSocket?: SocketFactory }) {
  const { sessionId, follow, restart, closeDialog, draft, setDraft } = useCaptureDialog();
  const capture = useStartCapture(follow);
  return (
    <CommandCapture open onOpenChange={(open) => (open ? undefined : closeDialog())}>
      {sessionId ? (
        <CaptureRun
          key={sessionId}
          sessionId={sessionId}
          onAgain={restart}
          onClose={closeDialog}
          createSocket={createSocket}
        />
      ) : (
        <CaptureInput
          draft={draft}
          onDraft={setDraft}
          busy={capture.pending}
          uploading={capture.uploading}
          error={capture.error}
          onSubmit={(source) => void capture.start(source)}
          onFile={(file) => void capture.start({ kind: "file", file })}
        />
      )}
    </CommandCapture>
  );
}
