import { t } from "@/shared/i18n/t";
import { DebriefView } from "../../components/DebriefView";
import { ExchangeList } from "../../components/ExchangeList";
import type { InterviewView } from "../../types";
import { REVISIONS_PATH } from "../../urls";

/** Ce que l'entretien a donné, dit selon son état : le débrief, ou ce qui manque et pourquoi. */
export function InterviewResult({ interview }: { interview: InterviewView }) {
  switch (interview.status) {
    case "done":
      return <DebriefView interview={interview} reviewsHref={REVISIONS_PATH} />;
    case "debrief_failed":
      return (
        <div className="flex flex-col gap-3">
          <p role="note" className="max-w-prose">
            {t("applications.interviewOutcome.debriefFailed")}
          </p>
          <h3 className="text-lg font-semibold">{t("applications.debrief.answers")}</h3>
          <ExchangeList exchanges={interview.exchanges} showNotes={false} />
        </div>
      );
    case "stopped":
      return <p className="max-w-prose">{t("applications.interviewOutcome.stopped")}</p>;
    case "failed":
      return <p className="max-w-prose">{t("applications.interviewOutcome.failed")}</p>;
    default:
      return <p>{t("applications.interviewOutcome.running")}</p>;
  }
}
