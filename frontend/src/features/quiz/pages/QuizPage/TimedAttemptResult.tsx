import { useRef, useState, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { concentrationDrop, type ResponseTiming } from "@/shared/lib/concentration";
import { ConcentrationPanel } from "@/shared/ui/ConcentrationPanel";
import { QuestionResult } from "../../components/QuizResult/QuestionResult";
import type { AttemptResultView } from "../../components/viewTypes";
import { AttemptResult } from "./AttemptResult";

interface Props {
  result: AttemptResultView;
  timings: ResponseTiming[] | undefined;
  refreshing: boolean;
  onBack: () => void;
  children?: ReactNode;
}

function slowed(result: AttemptResultView, timings: ResponseTiming[]) {
  const points = new Map(result.results.map((item) => [item.questionId, item.points]));
  return concentrationDrop(
    timings.flatMap(({ id, milliseconds }) => {
      const credit = points.get(id);
      return credit === undefined ? [] : [{ milliseconds, missed: credit < 1 }];
    }),
  );
}

export function TimedAttemptResult({ result, timings, refreshing, onBack, children }: Props) {
  const [choice, setChoice] = useState<"waiting" | "paused" | "review" | "closed">("waiting");
  const content = useRef<HTMLDivElement>(null);
  const recommend = choice === "waiting" && slowed(result, timings ?? []);
  const phase = recommend
    ? "suggested"
    : choice === "paused" || choice === "review"
      ? choice
      : null;
  const first = choice === "review" ? result.results.find((item) => item.points < 1) : undefined;
  const resume = () => {
    setChoice("closed");
    requestAnimationFrame(() => content.current?.focus());
  };
  return (
    <>
      {phase && (
        <ConcentrationPanel
          phase={phase}
          onPause={() => setChoice("paused")}
          onReview={() => setChoice("review")}
          onSummary={resume}
          onContinue={resume}
        >
          {first && (
            <>
              <p className="text-sm">{t("concentration.oneQuestion")}</p>
              <ul>
                <QuestionResult result={first} />
              </ul>
            </>
          )}
        </ConcentrationPanel>
      )}
      <div ref={content} tabIndex={-1} hidden={choice === "paused" || choice === "review"}>
        <div className="flex flex-col gap-4">
          <AttemptResult result={result} refreshing={refreshing} onBack={onBack} />
          {children}
        </div>
      </div>
    </>
  );
}
