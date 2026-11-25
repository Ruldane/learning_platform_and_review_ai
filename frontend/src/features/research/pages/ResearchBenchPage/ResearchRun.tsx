import { useMemo } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import type { SessionStream } from "@/shared/realtime/useSessionStream";
import {
  SessionControls,
  SessionStatusBar,
  SourcesPanel,
  sourcesFromEvents,
} from "@/shared/session-ui";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface ResearchRunProps {
  sessionId: string;
  stream: SessionStream;
  /** Leaves this test to start another one. */
  onRestart: () => void;
}

/**
 * A test followed live: status bar (cost included), sources, failure message, controls
 * (pause, cancel while the test is not finished) and new test.
 */
export function ResearchRun({ sessionId, stream, onRestart }: ResearchRunProps) {
  const { events, view, status, connection } = stream;
  const actions = useSessionActions(sessionId);
  const model = useMemo(() => sourcesFromEvents(events), [events]);

  if (connection === "failed") {
    // A session that cannot be found is not "retried": another test is offered.
    const missing = stream.failure === "not_found";
    return (
      <ErrorState
        message={stream.error ?? t("errors.generic")}
        onRetry={missing ? onRestart : stream.retry}
        actionLabel={missing ? t("research.page.again") : undefined}
      />
    );
  }
  if (connection === "connecting" && events.length === 0) {
    return <LoadingState label={t("research.page.loading")} />;
  }

  const failure = status === "failed" ? (view.error?.message ?? t("research.page.failed")) : null;
  return (
    <div className="flex flex-col gap-4">
      <SessionStatusBar status={status} cost={view.cost}
        playedBy={view.playedBy} waitingForClient={view.pendingInterrupt?.kind === "mcp_model"} />
      {connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("research.page.reconnecting")}
        </p>
      ) : null}
      <SourcesPanel model={model} pending={status === "running"} />
      {failure ? <InlineError message={failure} /> : null}
      {actions.error ? <InlineError message={actions.error} /> : null}
      <SessionControls
        status={status}
        onPause={() => void actions.pause()}
        onResume={() => void actions.resume(null, null)}
        onCancel={() => void actions.cancel()}
      />
      <Link to={{ search: "" }} className="self-start text-sm underline">
        {t("research.page.again")}
      </Link>
    </div>
  );
}
