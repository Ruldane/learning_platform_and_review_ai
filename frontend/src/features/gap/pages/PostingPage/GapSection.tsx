import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useGap } from "../../hooks/useGap";
import { useRelaunchGap } from "../../hooks/useRelaunchGap";
import { AnalysisRun } from "./AnalysisRun";
import { GapFailure } from "./GapFailure";
import { GapReady } from "./GapReady";
import { WaitingNotice } from "./WaitingNotice";

interface GapSectionProps {
  postingId: string;
  pollMs: number;
  createSocket?: SocketFactory;
}

/**
 * The « Écart avec ton profil » section of an analyzed posting: calculating (session feed,
 * 3 s re-read), failure with « Relancer », or the table.
 */
export function GapSection({ postingId, pollMs, createSocket }: GapSectionProps) {
  const { query, budget } = useGap(postingId, true, pollMs);
  const relaunch = useRelaunchGap(postingId, budget.restart);
  const gap = query.data;

  let body;
  if (gap === undefined) {
    body = query.isError ? (
      <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
    ) : (
      <LoadingState label={t("gap.posting.gapPending")} />
    );
  } else if (gap.status === "pending") {
    body = (
      <>
        <WaitingNotice
          label={t("gap.posting.gapPending")}
          exhausted={budget.exhausted}
          onContinue={() => {
            budget.restart();
            void query.refetch();
          }}
        />
        {gap.session_id ? (
          <AnalysisRun
            sessionId={gap.session_id}
            postingId={postingId}
            createSocket={createSocket}
          />
        ) : null}
      </>
    );
  } else if (gap.status === "failed") {
    body = <GapFailure relaunch={relaunch} />;
  } else {
    body = <GapReady postingId={postingId} gap={gap} />;
  }

  return (
    <section aria-label={t("gap.posting.gapTitle")} className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">{t("gap.posting.gapTitle")}</h2>
      {body}
    </section>
  );
}
