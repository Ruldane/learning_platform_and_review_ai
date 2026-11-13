import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { MAX_PLAN_SKILLS, type GapRowView } from "../viewTypes";
import { GapRow } from "./GapRow";
import { GapTableHead } from "./GapTableHead";

interface GapTableProps {
  rows: GapRowView[];
  /** Les compétences cochées (parmi celles « À ajouter »). */
  selected: string[];
  onToggle: (skill: string) => void;
  onAddToPlan: () => void;
  /** L'ajout au planning est en route. */
  adding: boolean;
}

/**
 * L'écart entre l'offre et le profil : compétence, exigence, niveau, action. On coche jusqu'à
 * `MAX_PLAN_SKILLS` compétences « À ajouter » puis « Ajouter au planning » les envoie d'un coup.
 */
export function GapTable({ rows, selected, onToggle, onAddToPlan, adding }: GapTableProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("gap.table.empty")}</p>;
  }
  const full = selected.length >= MAX_PLAN_SKILLS;
  const count = selected.length;
  const label = adding
    ? t("gap.table.adding")
    : count === 0
      ? t("gap.table.addNone")
      : t("gap.table.add", { count });
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
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={onAddToPlan} disabled={count === 0 || adding} aria-busy={adding}>
          {label}
        </Button>
        <p className="text-xs text-muted-foreground">
          {t("gap.table.limit", { max: MAX_PLAN_SKILLS })}
        </p>
      </div>
    </div>
  );
}
