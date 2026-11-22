import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { isAddable, MAX_PLAN_SKILLS, type GapRowView } from "../viewTypes";
import { GapActions } from "./GapActions";
import { GapRow } from "./GapRow";
import { GapTableHead } from "./GapTableHead";

interface GapTableProps {
  rows: GapRowView[];
  /** Les compétences cochées pour l'ajout au planning. */
  selected: string[];
  onToggle: (skill: string) => void;
  onAddToPlan: () => void;
  /** « Je les maîtrise déjà » : un quiz de validation pour les compétences cochées. */
  onValidate?: () => void;
  launchOptions?: ReactNode;
  /** L'ajout au planning est en route. */
  adding: boolean;
}

export function GapTable({
  rows,
  selected,
  onToggle,
  onAddToPlan,
  onValidate,
  launchOptions,
  adding,
}: GapTableProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("gap.table.empty")}</p>;
  }
  const full = selected.length >= MAX_PLAN_SKILLS;
  const validationCount = rows.filter((row) => selected.includes(row.skill) && isAddable(row)).length;
  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-xl border bg-card">
        <table aria-label={t("gap.table.label")} className="w-full text-sm">
          <GapTableHead />
          <tbody>
            {rows.map((row) => {
              const checked = selected.includes(row.skill);
              const locked = adding || (full && !checked);
              return (
                <GapRow
                  key={row.skill}
                  row={row}
                  checked={checked}
                  locked={locked}
                  onToggle={onToggle}
                />
              );
            })}
          </tbody>
        </table>
      </div>
      {launchOptions}
      <GapActions
        count={selected.length}
        validationCount={validationCount}
        adding={adding}
        onAddToPlan={onAddToPlan}
        onValidate={onValidate}
      />
    </div>
  );
}
