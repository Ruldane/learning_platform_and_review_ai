import { t } from "@/shared/i18n/t";
import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { CaptureEnd } from "./CaptureEnd";
import { useCaptureDialog } from "./captureDialog";
import { CaptureFeed } from "./components/CaptureFeed";
import { failureMessage } from "./errors";
import { useCaptureRun } from "./hooks/useCaptureRun";

interface CaptureRunProps {
  sessionId: string;
  /** Starts again from an empty field. */
  onAgain: () => void;
  /** Closes the dialog (before going to the journal). */
  onClose: () => void;
  /** Only used in tests (fake WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * Tracks a capture in the dialog: summary lines, concepts, the Archivist's questions,
 * then its end with the link to the journal. A failure states its reason in plain text.
 */
export function CaptureRun({ sessionId, onAgain, onClose, createSocket }: CaptureRunProps) {
  const { stream, actions, over } = useCaptureRun(sessionId, createSocket);
  const failure = stream.view.error;
  const textDraft = useCaptureDialog((state) => state.textDraft);
  const setTextDraft = useCaptureDialog((state) => state.setTextDraft);
  if (stream.connection === "failed") {
    return <ErrorState message={stream.error ?? t("errors.generic")} onRetry={stream.retry} />;
  }
  if (stream.connection === "connecting" && stream.events.length === 0) {
    return <LoadingState label={t("capture.run.loading")} />;
  }
  return (
    <section aria-label={t("capture.run.label")} className="flex flex-col gap-3">
      {stream.connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("capture.run.reconnecting")}
        </p>
      ) : null}
      <CaptureFeed
        items={stream.view.feed}
        isAwaiting={(id) => isAwaitingAnswer(stream.view, id)}
        pending={actions.pending}
        onAnswer={(id, value) => void actions.resume(id, value)}
        textDraft={textDraft}
        onTextDraft={setTextDraft}
      />
      {actions.error ? <InlineError message={actions.error} /> : null}
      {over ? (
        <CaptureEnd
          status={stream.status}
          failure={failure ? failureMessage(failure.code, failure.message) : null}
          onAgain={onAgain}
          onClose={onClose}
        />
      ) : null}
    </section>
  );
}
