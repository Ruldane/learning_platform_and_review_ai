import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import { InterruptCard } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useGenerate } from "../../hooks/useGenerate";
import type { Run } from "@/shared/realtime/useRun";
import type { CvReviewOut } from "../../types";

const PDF = "pdf";
const REPORT = "report";

interface OutputSectionProps {
  review: CvReviewOut;
  run: Run;
  generate: ReturnType<typeof useGenerate>;
}

/**
 * Viewing the report and finishing resume the session. Generating the PDF calls the render route.
 * The buttons are disabled during rendering and enabled when the question returns, even after a
 * reload.
 */
export function OutputSection({ review, run, generate }: OutputSectionProps) {
  const navigate = useNavigate();
  const { stream, actions } = run;
  const question = stream.pendingInterrupt?.kind === "cv_output" ? stream.pendingInterrupt : null;
  const open =
    question !== null &&
    review.waiting_output &&
    isAwaitingAnswer(stream.view, question.interrupt_id) &&
    !actions.pending &&
    !generate.pending;
  const answer = (value: unknown) => {
    if (question === null) return;
    if (value === PDF) {
      generate.generate(false);
      return;
    }
    void actions.resume(question.interrupt_id, value).then((ok) => {
      if (ok && value === REPORT) void navigate({ hash: "#report" });
    });
  };
  return (
    <div className="flex flex-col gap-3">
      {question !== null ? (
        <>
          <p className="text-sm text-muted-foreground">{t("cv.reviewPage.outputHint")}</p>
          <InterruptCard interrupt={question} answered={false} disabled={!open} onAnswer={answer} />
        </>
      ) : null}
      {generate.error ? <InlineError message={generate.error} /> : null}
    </div>
  );
}
