import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import { ProgressBar } from "../ProgressOverview/ProgressBar";
import type { ProgramSummaryView } from "../viewTypes";

/** A list card: title (link), state, start, number of weeks and progress bar. */
export function ProgramItem({ program }: { program: ProgramSummaryView }) {
  const weeksKey = program.weeks === 1 ? "program.page.weeksOne" : "program.page.weeksMany";
  return (
    <li className="rounded-lg border border-border bg-card p-4 focus-within:ring-2 focus-within:ring-ring">
      <Link
        to={`/learn/programs/${program.id}`}
        className="text-lg font-semibold break-words underline-offset-4 hover:underline focus-visible:outline-none"
      >
        {program.title}
      </Link>
      <p className="mt-1 flex flex-wrap gap-x-3 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">
          {t(`program.page.status.${program.status}`)}
        </span>
        <span>{t("program.page.start", { date: longDay(program.startDate) })}</span>
        <span>{t(weeksKey, { count: program.weeks })}</span>
      </p>
      <div className="mt-3 flex items-center gap-3">
        <ProgressBar
          label={t("program.page.progressLabel", { title: program.title })}
          percent={program.percent}
        />
        <span className="shrink-0 text-sm tabular-nums">
          {t("program.progress.percent", { percent: program.percent })}
        </span>
      </div>
    </li>
  );
}
