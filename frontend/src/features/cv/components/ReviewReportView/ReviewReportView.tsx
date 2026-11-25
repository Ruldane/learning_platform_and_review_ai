import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { ReportView } from "../viewTypes";
import { ReportList } from "./ReportList";

interface ReviewReportViewProps {
  report: ReportView;
  /** Job keywords the cited facts do not cover: to back with a fact or to acquire. */
  gapTerms: string[];
  /** The URL of the gap screen. */
  gapHref: string;
}

/**
 * The review report: strengths, risks, knockout criteria, detected applicant tracking system,
 * company profile, and job keywords the cited facts do not cover (never added to the CV).
 * Everything is rendered as plain text.
 */
export function ReviewReportView({ report, gapTerms, gapHref }: ReviewReportViewProps) {
  return (
    <section aria-label={t("cv.report.label")} className="flex flex-col gap-4">
      <ReportList title={t("cv.report.strengths")} items={report.strengths} />
      <ReportList title={t("cv.report.risks")} items={report.risks} />
      <ReportList title={t("cv.report.eliminatory")} items={report.eliminatory} />
      <section className="flex flex-col gap-1">
        <p className="text-sm font-medium">
          {report.ats ? t("cv.report.ats", { name: report.ats }) : t("cv.report.atsNone")}
        </p>
        {report.atsNotes.length > 0 ? (
          <ul className="list-disc pl-5 text-sm">
            {report.atsNotes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        ) : null}
      </section>
      {report.companySummary ? (
        <section className="flex flex-col gap-1">
          <h3 className="text-sm font-medium">{t("cv.report.company")}</h3>
          <p className="text-sm">{report.companySummary}</p>
        </section>
      ) : null}
      {gapTerms.length > 0 ? (
        <p className="text-sm">
          {t("cv.report.gap", { terms: gapTerms.join(", ") })}{" "}
          <Link to={gapHref} className="font-medium text-primary underline underline-offset-4">
            {t("cv.report.gapLink")}
          </Link>
        </p>
      ) : null}
    </section>
  );
}
