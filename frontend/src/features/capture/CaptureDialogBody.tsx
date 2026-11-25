import type { SocketFactory } from "@/shared/realtime/socket";
import { useCaptureDialog } from "./captureDialog";
import { CaptureInput, CommandCapture } from "./components/CommandCapture";
import { CaptureRun } from "./CaptureRun";
import { useStartCapture } from "./hooks/useStartCapture";

/**
 * The open dialog: the capture field, or the tracking of the started capture. Mounted only
 * when the dialog opens: while it is closed, no read or data provider
 * is needed (the shortcut lives in `CaptureOverlay`).
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
        <>
          {capture.launchMenu}
          <CaptureInput
            draft={draft}
            onDraft={setDraft}
            busy={capture.pending}
            uploading={capture.uploading}
            error={capture.error}
            onSubmit={(source) => void capture.start(source)}
            onFile={(file) => void capture.start({ kind: "file", file })}
          />
        </>
      )}
    </CommandCapture>
  );
}
