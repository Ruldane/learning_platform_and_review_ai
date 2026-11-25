import { LineChart, ResponsiveContainer } from "recharts";
import { t } from "@/shared/i18n/t";
import { shortDay } from "@/shared/lib/format";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { useReducedMotion } from "../useReducedMotion";
import type { HistoryPointView, LevelCounts } from "../viewTypes";
import { LEVELS, chartParts } from "./chartParts";

interface ProgressChartProps {
  points: HistoryPointView[];
  /** The action of the empty state (rule 15.4: never a dead end). */
  emptyAction?: { label: string; onClick: () => void };
}

function chartRows(points: HistoryPointView[]) {
  return [...points]
    .sort((a, b) => a.weekStart.localeCompare(b.weekStart))
    .map(({ weekStart, counts, score }) => ({ weekStart, ...counts, score }));
}

function countsText(counts: LevelCounts): string {
  return LEVELS.map((level) => `${t(`skills.level.${level}`)} ${counts[level]}`).join(", ");
}

/**
 * Progress curves, one reading per week: one curve per level (number of skills,
 * on the left) and the score from 0 to 100 (dotted, on the right). Last reading written below
 * the drawing for screen readers; the line does not animate when motion is reduced.
 */
export function ProgressChart({ points, emptyAction }: ProgressChartProps) {
  const reduced = useReducedMotion();
  if (points.length === 0) {
    return (
      <EmptyState
        title={t("skills.progress.empty")}
        description={t("skills.progress.emptyHint")}
        action={emptyAction}
      />
    );
  }
  const rows = chartRows(points);
  const latest = rows[rows.length - 1]!;
  return (
    <section aria-label={t("skills.progress.label")} className="flex flex-col gap-3">
      <div role="img" aria-label={t("skills.progress.label")} className="h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
            {chartParts(!reduced)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-sm text-muted-foreground">
        {t("skills.progress.latest", {
          day: shortDay(latest.weekStart),
          counts: countsText(latest),
          score: latest.score,
        })}
      </p>
    </section>
  );
}
