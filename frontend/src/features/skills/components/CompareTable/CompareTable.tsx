import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { CompareRowView } from "../viewTypes";
import { CompareGrid } from "./CompareGrid";
import { CoverageBar } from "./CoverageBar";

interface CompareTableProps {
  rows: CompareRowView[];
  /** Share of target skills reached, as a whole percentage. */
  coverage: number;
  targetLabel: string;
  /** The action of the empty state (rule 15.4: never a dead end). */
  emptyAction?: { label: string; onClick: () => void };
}

/**
 * Comparison between my level and the target role's: coverage first, then the skills
 * from largest gap to smallest (for equal gaps, the received order is kept).
 */
export function CompareTable({ rows, coverage, targetLabel, emptyAction }: CompareTableProps) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title={t("skills.compare.empty")}
        description={t("skills.compare.emptyHint")}
        action={emptyAction}
      />
    );
  }
  return (
    <section className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        {t("skills.compare.target", { target: targetLabel })}
      </p>
      <CoverageBar coverage={coverage} />
      <CompareGrid rows={rows} />
    </section>
  );
}
