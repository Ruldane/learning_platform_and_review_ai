import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { SessionControls, SessionStatusBar } from "@/shared/session-ui";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useReplanRun } from "../../hooks/useReplanRun";
import { ReplanEnd } from "./ReplanEnd";
import { ReplanFeed } from "./ReplanFeed";

interface ReplanRunProps {
  sessionId: string;
  programId: string;
  onAgain: () => void;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

/** Une replanification suivie en direct : état, fil du Stratège, commandes, puis sa fin. */
export function ReplanRun({ sessionId, programId, onAgain, createSocket }: ReplanRunProps) {
  const run = useReplanRun(sessionId, programId, createSocket);
  const { stream, actions, over } = run;
  if (stream.connection === "failed") {
    return <ErrorState message={stream.error ?? t("errors.generic")} onRetry={stream.retry} />;
  }
  if (stream.connection === "connecting" && stream.events.length === 0) {
    return <LoadingState label={t("replan.loading")} />;
  }
  return (
    <section aria-label={t("replan.run.label")} className="flex flex-col gap-3">
      <SessionStatusBar status={stream.status} cost={stream.view.cost} />
      <ReplanFeed run={run} />
      <SessionControls
        status={stream.status}
        onPause={() => void actions.pause()}
        onResume={() => void actions.resume(null, null)}
        onCancel={() => void actions.cancel()}
      />
      {over ? (
        <ReplanEnd
          programId={programId}
          status={stream.status}
          failure={stream.view.error?.message ?? null}
          onAgain={onAgain}
        />
      ) : null}
    </section>
  );
}
