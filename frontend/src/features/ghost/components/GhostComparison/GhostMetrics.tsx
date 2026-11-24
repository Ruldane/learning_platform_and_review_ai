import { t } from "@/shared/i18n/t";

import type { Metrics } from "./viewTypes";

const duration = new Intl.NumberFormat("en-GB", {
  style: "unit",
  unit: "second",
  maximumFractionDigits: 2,
});

interface Props {
  title: string;
  kind: "ide" | "quiz";
  values: Metrics;
  ticking?: boolean;
}

export function GhostMetrics({ title, kind, values, ticking = false }: Props) {
  const unavailable = t("ghost.unavailable");
  const { duration: elapsed, errors, completed: progress, total } = values;
  const time = elapsed === null ? unavailable : duration.format(elapsed / 1000);
  const progressLabel = t(kind === "quiz" ? "ghost.quizProgress" : "ghost.ideProgress");
  return (
    <div className="rounded-lg border px-3 py-2">
      <h3 className="mb-1 font-medium">{title}</h3>
      <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1">
        <dt>{t(kind === "quiz" ? "ghost.quizTime" : "ghost.ideTime")}</dt>
        <dd role={ticking ? "timer" : undefined}>{time}</dd>
        <dt>{progressLabel}</dt>
        <dd>
          {progress === null ? unavailable : total === null ? progress : `${progress} / ${total}`}
        </dd>
        <dt>{t(kind === "quiz" ? "ghost.quizIssues" : "ghost.ideIssues")}</dt>
        <dd>{errors ?? unavailable}</dd>
        {values.score != null && (
          <>
            <dt>{t("ghost.score")}</dt>
            <dd>{values.score} %</dd>
          </>
        )}
      </dl>
    </div>
  );
}
