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
 * Le lien `#rapport` (rapport demandé dans le fil) mène à la section du rapport et place le focus
 * sur son titre : au clavier ou au lecteur d'écran, la lecture continue là où l'on vient d'aller.
 * La clé de l'adresse change à chaque navigation, un second clic sur « Voir le rapport » compris.
 */
function useScrollToReport(ready: boolean) {
  const { hash, key } = useLocation();
  useEffect(() => {
    if (!ready || hash !== "#rapport") return;
    document.getElementById("rapport")?.scrollIntoView?.();
    document.getElementById("rapport-titre")?.focus();
  }, [ready, hash, key]);
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
