import { useMemo, useState } from "react";
import { useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useVersions } from "../../hooks/useVersions";
import { useWaitingReplan } from "../../hooks/useWaitingReplan";
import { decisionOf, pendingVersion, toVersionView } from "../../toView";
import { ProposalPanel } from "./ProposalPanel";
import { ReplanHeader } from "./ReplanHeader";
import { ReplanHistory } from "./ReplanHistory";
import { ReplanRun } from "./ReplanRun";
import { ReplanStart } from "./ReplanStart";

/**
 * Replanning a program (`/learn/programs/:programId/replan`). Without a replan in progress:
 * the form (hours available, message). With one: the proposal (changes, load, cap),
 * the Strategist's thread and the card to accept or refuse. A replan already awaiting an answer is
 * joined automatically, and stays followed after its end (it no longer waits, but its end message
 * must stay on screen).
 */
export function ReplanPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { programId = "" } = useParams();
  const versions = useVersions(programId);
  const waiting = useWaitingReplan(programId);
  // `undefined`: follow the waiting session (if one exists); `null`: a new request.
  const [followed, setFollowed] = useState<string | null | undefined>(undefined);
  const sessionId = followed === undefined ? (waiting.data ?? null) : followed;
  // The joined session is frozen (adjusted during render, no effect): the final re-read,
  // where nothing waits any more, does not make it forgotten.
  if (followed === undefined && waiting.data) setFollowed(waiting.data);
  const views = useMemo(() => versions.data?.map(toVersionView), [versions.data]);
  const proposal = sessionId && views ? pendingVersion(views) : null;

  return (
    <div className="flex flex-col gap-6">
      <ReplanHeader programId={programId} />
      {waiting.isPending ? <LoadingState label={t("replan.loading")} /> : null}
      {waiting.isError ? (
        <ErrorState message={errorMessage(waiting.error)} onRetry={() => void waiting.refetch()} />
      ) : null}
      {proposal ? <ProposalPanel version={proposal} /> : null}
      {waiting.isSuccess && sessionId === null ? (
        <ReplanStart programId={programId} onSession={setFollowed} />
      ) : null}
      {sessionId !== null ? (
        <ReplanRun
          key={sessionId}
          sessionId={sessionId}
          programId={programId}
          onAgain={() => setFollowed(null)}
          decision={decisionOf(views, sessionId)}
          createSocket={createSocket}
        />
      ) : null}
      <ReplanHistory
        programId={programId}
        versions={views}
        loading={versions.isPending}
        error={versions.error}
        onRetry={() => void versions.refetch()}
      />
    </div>
  );
}
