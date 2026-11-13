import { t } from "@/shared/i18n/t";

const COLUMNS = ["skill", "required", "level", "action"] as const;

/** L'en-tête du tableau d'écart : la colonne des cases (lue « Sélection ») puis les quatre colonnes. */
export function GapTableHead() {
  return (
    <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
      <tr>
        <th scope="col" className="px-2 py-2">
          <span className="sr-only">{t("gap.table.select")}</span>
        </th>
        {COLUMNS.map((column) => (
          <th key={column} scope="col" className="px-2 py-2">
            {t(`gap.table.${column}`)}
          </th>
        ))}
      </tr>
    </thead>
  );
}
