import { t } from "@/shared/i18n/t";
import { formatMinutes, shortDay } from "@/shared/lib/format";
import type { WeekLoadView } from "../viewTypes";

interface WeekLoadTableProps {
  loads: WeekLoadView[];
}

/** L'état d'une semaine face à son plafond, en toutes lettres (jamais par la couleur seule). */
function stateOf(load: WeekLoadView) {
  if (load.after > load.cap) return t("replan.loads.over");
  return load.after === load.cap ? t("replan.loads.atCap") : t("replan.loads.under");
}

const HEAD = "px-3 py-1.5 font-medium";

/**
 * La charge de chaque semaine avant et après la proposition, face à son plafond (85 % du budget).
 * Les durées sont écrites en heures et minutes ; l'état de la semaine est dit en mots.
 */
export function WeekLoadTable({ loads }: WeekLoadTableProps) {
  if (loads.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("replan.loads.empty")}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{t("replan.loads.caption")}</caption>
        <thead>
          <tr className="border-b text-muted-foreground">
            <th scope="col" className={HEAD}>
              {t("replan.loads.week")}
            </th>
            <th scope="col" className={`${HEAD} text-right`}>
              {t("replan.loads.before")}
            </th>
            <th scope="col" className={`${HEAD} text-right`}>
              {t("replan.loads.after")}
            </th>
            <th scope="col" className={`${HEAD} text-right`}>
              {t("replan.loads.cap")}
            </th>
            <th scope="col" className={HEAD}>
              {t("replan.loads.state")}
            </th>
          </tr>
        </thead>
        <tbody>
          {loads.map((load) => (
            <tr key={load.rank} className="border-b last:border-b-0">
              <th scope="row" className="px-3 py-1.5 font-normal">
                {t("replan.loads.weekValue", { rank: load.rank, day: shortDay(load.startDate) })}
              </th>
              <td className="px-3 py-1.5 text-right tabular-nums">{formatMinutes(load.before)}</td>
              <td className="px-3 py-1.5 text-right font-medium tabular-nums">
                {formatMinutes(load.after)}
              </td>
              <td className="px-3 py-1.5 text-right tabular-nums">{formatMinutes(load.cap)}</td>
              <td className="px-3 py-1.5">{stateOf(load)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
