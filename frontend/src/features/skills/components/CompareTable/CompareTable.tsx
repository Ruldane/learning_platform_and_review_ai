import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { CompareRowView } from "../viewTypes";
import { CompareGrid } from "./CompareGrid";
import { CoverageBar } from "./CoverageBar";

interface CompareTableProps {
  rows: CompareRowView[];
  /** Part des compétences cibles atteintes, en pourcentage entier. */
  coverage: number;
  targetLabel: string;
}

/**
 * Comparaison entre mon niveau et celui du poste cible : couverture en tête, puis les compétences
 * du plus grand écart au plus petit (à écart égal, l'ordre reçu est gardé).
 */
export function CompareTable({ rows, coverage, targetLabel }: CompareTableProps) {
  if (rows.length === 0) {
    return (
      <EmptyState title={t("skills.compare.empty")} description={t("skills.compare.emptyHint")} />
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
