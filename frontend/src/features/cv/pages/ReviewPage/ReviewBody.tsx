import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useLocation } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ReviewReportView } from "../../components/ReviewReportView";
import { useGenerate } from "../../hooks/useGenerate";
import { useRun } from "../../hooks/useRun";
import { cvKeys } from "../../queryKeys";
import { latestVersion, toReportView } from "../../toView";
import type { CvReviewOut } from "../../types";
import { RunFeed } from "../RunFeed";
import { DiffSection } from "./DiffSection";
import { IndicatorsSection } from "./IndicatorsSection";
import { OutputSection } from "./OutputSection";
import { Section } from "./Section";
import { VersionPanel } from "./VersionPanel";

const OUTPUT_QUESTION = "cv_output";

/** Le lien `#rapport` (rapport demandé dans le fil) mène à la section du rapport. */
function useScrollToReport(ready: boolean) {
  const { hash } = useLocation();
  useEffect(() => {
    if (ready && hash === "#rapport") document.getElementById("rapport")?.scrollIntoView?.();
  }, [ready, hash]);
}

interface ReviewBodyProps {
  review: CvReviewOut;
  createSocket?: SocketFactory;
}

/** Le corps de la revue : toutes ses parties, dans l'ordre où on les lit. */
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
          // La question de sortie ouverte vit dans la section « Sortie », sous les décisions.
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
        <Section title={t("cv.reviewPage.report")} id="rapport">
          <ReviewReportView
            report={toReportView(review.report)}
            gapTerms={review.gap_terms}
            gapHref={`/carriere/offres/${review.posting_id}`}
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
