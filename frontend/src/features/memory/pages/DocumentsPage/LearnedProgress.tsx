import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";

interface LearnedProgressProps {
  /** `learned_document` session started by « Déjà appris ». */
  sessionId: string;
  documentName: string;
  /** Called once, when the session ends (successful or not). */
  onFinished: () => void;
  /** Restarts the Archivist run on the document (failure or cancellation). */
  onRetry: () => void;
  createSocket?: SocketFactory;
}

const FINISHED = ["completed", "failed", "cancelled", "expired"];

/**
 * The Archivist's progress on a document, read from the session stream: « extracts the
 * concepts » while running, then the number of acquired items written (confirmed
 * `memory.written` events), or the failure message.
 */
export function LearnedProgress({
  sessionId,
  documentName,
  onFinished,
  onRetry,
  createSocket,
}: LearnedProgressProps) {
  const stream = useSessionStream(sessionId, { createSocket });
  const { status, events, view } = stream;
  const finished = FINISHED.includes(status);
  const callback = useRef(onFinished);
  useEffect(() => {
    callback.current = onFinished;
  });
  useEffect(() => {
    if (finished) callback.current();
  }, [finished]);

  if (stream.connection === "failed") {
    return <ErrorState message={stream.error ?? t("errors.generic")} onRetry={stream.retry} />;
  }
  // A proposed decision (`status: "pending"`) waits for the user's agreement: not an added item.
  const written = events.filter(
    (event) => event.type === "memory.written" && event.payload.status !== "pending",
  ).length;
  const failed = status === "failed" || status === "cancelled";
  const message = !finished
    ? t("memory.documents.learning")
    : failed
      ? (view.error?.message ?? t("memory.documents.learnedFailed"))
      : t("memory.documents.learnedCount", { n: written });

  return (
    <section
      aria-label={t("memory.documents.learnedProgress", { name: documentName })}
      className="flex flex-col gap-1 rounded-lg border border-border bg-card px-3 py-2"
    >
      <p className="text-sm font-medium break-words">{documentName}</p>
      <p
        role={failed ? "alert" : "status"}
        className={failed ? "text-sm text-destructive" : "text-sm"}
      >
        {message}
      </p>
      {failed ? (
        <Button variant="outline" size="sm" className="self-start" onClick={onRetry}>
          {t("memory.documents.relaunch")}
        </Button>
      ) : null}
    </section>
  );
}
