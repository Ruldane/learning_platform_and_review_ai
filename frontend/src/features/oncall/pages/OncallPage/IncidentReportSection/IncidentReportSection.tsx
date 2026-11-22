import { t } from "@/shared/i18n/t";
import { IncidentReport } from "../../../components/IncidentReport";
import { ReviewResult } from "../../../components/ReviewResult";
import type { Incident } from "../../../types";

interface IncidentReportSectionProps {
  incident: Incident;
  busy: boolean;
  onReport: (report: string) => void;
}

export function IncidentReportSection({ incident, busy, onReport }: IncidentReportSectionProps) {
  const review = incident.review_state;
  const observed = incident.events.some((event) => incident.observed_events.includes(event.id));
  const reviewMessage =
    review === "running"
      ? t("oncall.reviewing")
      : review === "failed"
        ? t("oncall.reviewFailed")
        : null;
  return (
    <>
      <IncidentReport
        report={incident.report ?? ""}
        ready={incident.diagnostic.state === "passed" && observed}
        verified={incident.proof_recorded}
        disabled={busy || review === "running"}
        reviewMessage={reviewMessage}
        onReport={onReport}
      />
      {incident.verdict && (
        <ReviewResult
          scores={incident.verdict}
          feedback={incident.verdict.feedback}
          proof={incident.proof_recorded}
        />
      )}
    </>
  );
}
