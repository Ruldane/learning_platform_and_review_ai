import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useCouncilData } from "../../hooks/useCouncilData";
import { useCouncilSession } from "../../hooks/useCouncilSession";
import { useCouncilTabs } from "../../hooks/useCouncilTabs";
import { useProgramRetry } from "../../hooks/useProgramRetry";
import { useRetryCouncil } from "../../hooks/useRetryCouncil";
import type { GoalOut } from "../../types";
import { CouncilFeed } from "./CouncilFeed";
import { CouncilSide } from "./CouncilSide";
import { CouncilStatus } from "./CouncilStatus";

interface CouncilLayoutProps {
  goal: GoalOut;
  sessionId: string;
  createSocket?: SocketFactory;
}

/**
 * A goal's Council (SPEC 15.2): status bar on top, debate on the left (40 %), board,
 * sources and proposals on the right (60 %). A dropped stream or a session not found are reported
 * here; the session is found again through the goal's id (resumed after a reload).
 */
export function CouncilLayout({ goal, sessionId, createSocket }: CouncilLayoutProps) {
  const navigate = useNavigate();
  const session = useCouncilSession(goal, sessionId, createSocket);
  const data = useCouncilData(goal.id, sessionId, session.stream.events);
  const tabs = useCouncilTabs(session.progress.stage);
  const councilRetry = useRetryCouncil(goal.id, sessionId);
  const programRetry = useProgramRetry(goal.id, sessionId, data.proposals.data);
  const { stream } = session;

  if (stream.connection === "failed") {
    // A session not found is not retried: back to the goals.
    const missing = stream.failure === "not_found";
    return (
      <ErrorState
        message={stream.error ?? t("errors.generic")}
        onRetry={missing ? () => void navigate("/learn/goals") : stream.retry}
        actionLabel={missing ? t("learning.council.goalsLink") : undefined}
      />
    );
  }
  if (stream.connection === "connecting" && stream.events.length === 0) {
    return <LoadingState label={t("learning.council.loading")} />;
  }
  return (
    <div className="flex flex-col gap-4">
      <CouncilStatus session={session} programRetry={programRetry} />
      <div className="grid items-start gap-6 lg:grid-cols-[2fr_3fr]">
        <CouncilFeed
          session={session}
          retry={councilRetry}
          onShowProposals={() => tabs.setTab("proposals")}
        />
        <CouncilSide session={session} data={data} tabs={tabs} />
      </div>
    </div>
  );
}
