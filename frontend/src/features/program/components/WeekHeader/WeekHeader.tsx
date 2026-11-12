import { t } from "@/shared/i18n/t";
import { formatMinutes } from "../format";
import type { WeekView } from "../viewTypes";

interface WeekHeaderProps {
  week: WeekView;
}

/** Entête d'une semaine : thème, objectif, livrable et charge face au plafond de 85 %. */
export function WeekHeader({ week }: WeekHeaderProps) {
  const over = week.loadMinutes > week.capMinutes;
  return (
    <header className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      <h2 className="text-lg font-semibold">
        {t("program.week.title", { rank: week.rank, theme: week.theme })}
      </h2>
      <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="text-muted-foreground">{t("program.week.objective")}</dt>
        <dd>{week.objective}</dd>
        <dt className="text-muted-foreground">{t("program.week.deliverable")}</dt>
        <dd>{week.deliverable}</dd>
        <dt className="text-muted-foreground">{t("program.week.load")}</dt>
        <dd>
          <p className="font-medium tabular-nums">
            {t("program.week.loadValue", {
              load: formatMinutes(week.loadMinutes),
              cap: formatMinutes(week.capMinutes),
            })}
          </p>
          <p className={over ? "text-destructive" : "text-muted-foreground"}>
            {over ? t("program.week.overCap") : t("program.week.withinCap")}
          </p>
        </dd>
      </dl>
    </header>
  );
}
