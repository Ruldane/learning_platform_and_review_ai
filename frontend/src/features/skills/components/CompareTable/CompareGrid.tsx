import { t } from "@/shared/i18n/t";
import type { CompareRowView } from "../viewTypes";
import { LevelCell } from "./LevelCell";

const HEADERS = ["skill", "domain", "mine", "wanted", "gap"] as const;

function gapText(gap: number): string {
  if (gap <= 0) return t("skills.compare.gapNone");
  return t(gap === 1 ? "skills.compare.gapSome" : "skills.compare.gapMany", { gap });
}

/** Le tableau : une ligne par compétence cible, le plus grand écart en premier. */
export function CompareGrid({ rows }: { rows: CompareRowView[] }) {
  const sorted = [...rows].sort((a, b) => b.gap - a.gap);
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table aria-label={t("skills.compare.label")} className="w-full text-left text-sm">
        <thead className="bg-muted">
          <tr>
            {HEADERS.map((header) => (
              <th key={header} scope="col" className="px-3 py-2 font-medium">
                {t(`skills.compare.${header}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={row.skillId} className="border-t">
              <td className="px-3 py-2 font-medium">{row.name}</td>
              <td className="px-3 py-2 text-muted-foreground">{row.domain}</td>
              <LevelCell level={row.mine} />
              <LevelCell level={row.target} />
              <td className="px-3 py-2">{gapText(row.gap)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
