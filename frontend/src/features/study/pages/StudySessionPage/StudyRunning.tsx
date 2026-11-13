import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useStudyRun } from "../../hooks/useStudyRun";
import { useStudySummary } from "../../hooks/useStudySummary";
import type { StudySessionOut } from "../../types";
import { SessionBoard } from "./SessionBoard";
import { SessionFeed } from "./SessionFeed";
import { SessionHeader } from "./SessionHeader";
import { SummaryWait } from "./SummaryWait";

/** Durées du minuteur tant que les réglages ne sont pas lus. */
const DEFAULT_WORK = 50;
const DEFAULT_BREAK = 10;

interface StudyRunningProps {
  session: StudySessionOut;
  finishing: boolean;
  onFinishing: () => void;
  /** L'attente du bilan est trop longue : proposer de le relire. */
  summaryLate: boolean;
  onRetrySummary: () => void;
  createSocket?: SocketFactory;
}

/**
 * Une session d'étude qui n'est pas terminée : en-tête (minuteur, « Terminer »), échange avec le
 * Tuteur à gauche (40 %) et tableau à droite (60 %). L'en-tête reste monté quoi qu'il arrive au
 * flux : le minuteur ne repart pas de zéro. Une fois « Terminer » accepté, le bilan s'écrit.
 */
export function StudyRunning(props: StudyRunningProps) {
  const { session, finishing, onFinishing, summaryLate, onRetrySummary, createSocket } = props;
  const settings = useStudySummary();
  const run = useStudyRun({ session, finishing, onFinishing, createSocket });
  const { stream } = run;
  const live = session.status === "open";
  const failed = live && stream.connection === "failed";
  const opening = live && stream.connection === "connecting" && stream.events.length === 0;

  return (
    <div className="flex flex-col gap-4">
      <SessionHeader
        session={session}
        run={run}
        finishing={finishing}
        workMinutes={settings.data?.work_minutes ?? DEFAULT_WORK}
        breakMinutes={settings.data?.break_minutes ?? DEFAULT_BREAK}
      />
      {finishing ? <SummaryWait late={summaryLate} onRetry={onRetrySummary} /> : null}
      {failed ? (
        <ErrorState message={stream.error ?? t("errors.generic")} onRetry={stream.retry} />
      ) : null}
      {opening ? <LoadingState label={t("study.session.loading")} /> : null}
      {failed || opening ? null : (
        <div className="grid items-start gap-6 lg:grid-cols-[2fr_3fr]">
          <SessionFeed run={run} live={live} finishing={finishing} />
          <SessionBoard events={stream.events} />
        </div>
      )}
    </div>
  );
}
