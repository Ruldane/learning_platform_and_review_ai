import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import type { PollingBudget } from "@/shared/lib/usePollingBudget";
import { useRelaunchGap } from "../../hooks/useRelaunchGap";
import type { PostingOut } from "../../types";
import { AnalysisRun } from "./AnalysisRun";
import { PostingOutcome } from "./PostingOutcome";
import { ReadyBlock } from "./ReadyBlock";
import { WaitingNotice } from "./WaitingNotice";

interface PostingBodyProps {
  posting: PostingOut;
  budget: PollingBudget;
  pollMs: number;
  onRetry: () => void;
  createSocket?: SocketFactory;
}

/** Le corps de la page selon l'état de l'offre : analyse, refus, échec ou offre analysée. */
export function PostingBody({ posting, budget, pollMs, onRetry, createSocket }: PostingBodyProps) {
  const relaunch = useRelaunchGap(posting.id, budget.restart);
  switch (posting.status) {
    case "analyzing":
      return (
        <>
          <WaitingNotice
            label={t("gap.posting.analyzing")}
            hint={t("gap.posting.analyzingHint")}
            exhausted={budget.exhausted}
            onContinue={() => {
              budget.restart();
              onRetry();
            }}
          />
          {posting.gap_session_id ? (
            <AnalysisRun
              sessionId={posting.gap_session_id}
              postingId={posting.id}
              createSocket={createSocket}
            />
          ) : null}
        </>
      );
    case "ready":
      return <ReadyBlock posting={posting} pollMs={pollMs} createSocket={createSocket} />;
    default:
      return (
        <PostingOutcome
          status={posting.status}
          reason={posting.failure_reason}
          relaunching={relaunch.pending}
          error={relaunch.error}
          launchOptions={relaunch.providerMenu}
          onRelaunch={relaunch.relaunch}
        />
      );
  }
}
