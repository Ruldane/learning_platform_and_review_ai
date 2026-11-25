import { t } from "@/shared/i18n/t";
import { canPlan, isAddable, type GapRowView } from "../viewTypes";

interface GapRowProps {
  row: GapRowView;
  checked: boolean;
  /** The box is greyed out: the selection limit is reached (or an add is in progress). */
  locked: boolean;
  onToggle: (skill: string) => void;
}

function actionText(row: GapRowView): string {
  if (row.action === "in_program") {
    return row.week === null
      ? t("gap.table.inProgramNoWeek")
      : t("gap.table.inProgram", { week: row.week });
  }
  if (row.action === "to_add") {
    return isAddable(row) ? t("gap.table.toAdd") : t("gap.table.acquired");
  }
  return t("gap.table.outOfScope");
}

export function GapRow({ row, checked, locked, onToggle }: GapRowProps) {
  return (
    <tr className="border-t align-top">
      <td className="w-10 px-2 py-2">
        {canPlan(row) ? (
          <input
            type="checkbox"
            checked={checked}
            disabled={locked}
            onChange={() => onToggle(row.skill)}
            aria-label={t("gap.table.selectRow", { skill: row.skill })}
          />
        ) : null}
      </td>
      <th scope="row" className="px-2 py-2 text-left font-medium">
        {row.skill}
        {row.source === "cv_review" ? (
          <span className="block text-xs font-normal text-muted-foreground">
            {t("gap.table.fromReview")}
          </span>
        ) : null}
      </th>
      <td className="px-2 py-2">{row.required ? t("gap.table.yes") : t("gap.table.no")}</td>
      <td className="px-2 py-2">{t(`gap.level.${row.level ?? "absent"}`)}</td>
      <td className="px-2 py-2">{actionText(row)}</td>
    </tr>
  );
}
