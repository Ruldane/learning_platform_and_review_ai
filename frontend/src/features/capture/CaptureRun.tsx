import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import type { SocketFactory } from "@/shared/realtime/socket";
import { Button, buttonVariants } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { CaptureFeed } from "./components/CaptureFeed";
import { failureMessage } from "./errors";
import { useCaptureRun } from "./hooks/useCaptureRun";

interface CaptureRunProps {
  sessionId: string;
  /** Repart d'un champ vide. */
  onAgain: () => void;
  /** Ferme le dialogue (avant d'aller au journal). */
  onClose: () => void;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

const OUTCOME = {
  completed: "capture.run.completed",
  failed: "capture.run.failed",
  cancelled: "capture.run.cancelled",
} as const;

/**
 * Le suivi d'une capture dans le dialogue : résumé en lignes, concepts, questions de l'Archiviste,
 * puis sa fin avec le lien vers le journal. Un échec dit sa raison en clair.
 */
export function CaptureRun({ sessionId, onAgain, onClose, createSocket }: CaptureRunProps) {
  const { stream, actions, over } = useCaptureRun(sessionId, createSocket);
  const failure = stream.view.error;
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
      />
      {actions.error ? <InlineError message={actions.error} /> : null}
      {over ? (
        <div className="flex flex-col gap-2 rounded-xl border bg-card p-3">
          <p role="status" className="font-semibold">
            {t(
              OUTCOME[
                stream.status === "failed" || stream.status === "cancelled"
                  ? stream.status
                  : "completed"
              ],
            )}
          </p>
          {failure ? <InlineError message={failureMessage(failure.code, failure.message)} /> : null}
          <div className="flex flex-wrap gap-2">
            <Link to="/etudier/journal" onClick={onClose} className={buttonVariants()}>
              {t("capture.run.journal")}
            </Link>
            <Button variant="outline" onClick={onAgain}>
              {t("capture.run.again")}
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
