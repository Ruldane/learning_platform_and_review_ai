import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";

interface LearnedProgressProps {
  /** Session `learned_document` lancée par « Déjà appris ». */
  sessionId: string;
  documentName: string;
  /** Appelé une fois, quand la session est terminée (réussie ou non). */
  onFinished: () => void;
  /** Relance le parcours de l'Archiviste sur le document (échec ou annulation). */
  onRetry: () => void;
  createSocket?: SocketFactory;
}

const FINISHED = ["completed", "failed", "cancelled"];

/**
 * Avancement de l'Archiviste pour un document, lu dans le flux de la session : « extrait les
 * concepts » pendant l'exécution, puis le nombre d'acquis écrits (événements `memory.written`
 * confirmés) ou le message de l'échec.
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
  // Une décision proposée (`status: "pending"`) attend l'accord de l'utilisateur : pas un acquis ajouté.
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
