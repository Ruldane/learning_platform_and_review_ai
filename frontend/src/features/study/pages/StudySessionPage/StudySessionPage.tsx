import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { SUMMARY_POLL_MS, useStudySession } from "../../hooks/useStudySession";
import { LoadFailed } from "./LoadFailed";
import { StudyEnd } from "./StudyEnd";
import { StudyRunning } from "./StudyRunning";

interface StudySessionPageProps {
  /** Only for tests (fake WebSocket). */
  createSocket?: SocketFactory;
  /** Summary reread interval, in ms (shortened by the tests). */
  pollMs?: number;
}

/**
 * A study session (`/study/session/:studyId`). Open: the Tutor, the timer and the
 * table. Finished: the summary (reread until `finished` after « Terminer »). Abandoned or
 * not found: an empty state that leads back to the start. A failed background reread is said in a
 * line, without replacing the page (the timer stays mounted).
 */
export function StudySessionPage({
  createSocket,
  pollMs = SUMMARY_POLL_MS,
}: StudySessionPageProps) {
  const { studyId = "" } = useParams();
  const navigate = useNavigate();
  const [finishing, setFinishing] = useState(false);
  const { query, budget } = useStudySession(studyId, finishing, pollMs);
  const home = () => void navigate("/study/session");

  if (query.isPending) return <LoadingState label={t("study.session.loading")} />;
  if (query.isError && query.data === undefined) {
    return <LoadFailed error={query.error} onRetry={() => void query.refetch()} onHome={home} />;
  }
  const session = query.data;
  const failure =
    query.isError && !query.isFetching ? (
      <InlineError message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
    ) : null;
  if (session.status === "finished") return <StudyEnd session={session} />;
  if (session.status === "cancelled") {
    return (
      <EmptyState
        title={t("study.session.cancelledTitle")}
        description={t("study.session.cancelledDescription")}
        action={{ label: t("study.session.newBlock"), onClick: home }}
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {failure}
      <StudyRunning
        key={session.id}
        session={session}
        finishing={finishing}
        onFinishing={() => setFinishing(true)}
        summaryLate={finishing && budget.exhausted}
        onRetrySummary={() => {
          budget.restart();
          void query.refetch();
        }}
        createSocket={createSocket}
      />
    </div>
  );
}
