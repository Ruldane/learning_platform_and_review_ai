import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useLocation } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { ReviewReportView } from "../../components/ReviewReportView";
import { useGenerate } from "../../hooks/useGenerate";
import { cvKeys } from "../../queryKeys";
import { latestVersion, toReportView } from "../../toView";
import type { CvReviewOut } from "../../types";
import { DiffSection } from "./DiffSection";
import { IndicatorsSection } from "./IndicatorsSection";
import { OutputSection } from "./OutputSection";
import { Section } from "./Section";
import { VersionPanel } from "./VersionPanel";

const OUTPUT_QUESTION = "cv_output";

/**
 * Focus the report heading when opening a report link. The location key also handles repeated
 * visits to the same fragment.
 */
function useScrollToReport(ready: boolean) {
  const { hash, key } = useLocation();
  useEffect(() => {
    if (!ready || (hash !== "#report" && hash !== "#rapport")) return;
    document.getElementById("report")?.scrollIntoView?.();
    document.getElementById("report-title")?.focus();
  }, [ready, hash, key]);
}

interface ReviewBodyProps {
  review: CvReviewOut;
  createSocket?: SocketFactory;
}

/** The review body: all its parts, in the order they are read. */
export function ReviewBody({ review, createSocket }: ReviewBodyProps) {
  const client = useQueryClient();
  const reload = () => void client.invalidateQueries({ queryKey: cvKeys.review(review.id) });
  const run = useRun(review.session_id, reload, createSocket);
  const generate = useGenerate(review.id);
  const closed = review.status !== "running" && review.status !== "proposed";
  useScrollToReport(review.report !== null);

  return (
    <>
      {review.session_id ? (
        <RunFeed
          run={run}
          label={t("cv.reviewPage.feed")}
          // The open exit question lives in the « Sortie » section, under the decisions.
          renderInterrupt={(item) =>
            item.interrupt.kind === OUTPUT_QUESTION && !item.answered ? null : undefined
          }
        />
      ) : null}
      <IndicatorsSection review={review} />
      <Section title={t("cv.reviewPage.modifications")}>
        <DiffSection review={review} locked={closed} />
      </Section>
      {review.report ? (
        <Section title={t("cv.reviewPage.report")} id="report">
          <ReviewReportView
            report={toReportView(review.report)}
            gapTerms={review.gap_terms}
            gapHref={`/career/postings/${review.posting_id}`}
          />
        </Section>
      ) : null}
      <Section title={t("cv.reviewPage.output")}>
        <OutputSection review={review} run={run} generate={generate} />
        <VersionPanel review={review} version={latestVersion(review)} generate={generate} />
      </Section>
    </>
  );
}
