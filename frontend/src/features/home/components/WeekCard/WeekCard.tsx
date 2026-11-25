import { formatMinutes } from "@/shared/lib/format";
import { t } from "@/shared/i18n/t";
import type { WeekView } from "../viewTypes";

interface WeekCardProps {
  /** Progress of the program's week; `null` without a validated program. */
  week: WeekView | null;
  /** The week source was down this morning: neither « aucune semaine » nor figures. */
  unavailable?: boolean;
}

function streakText(days: number): string {
  if (days <= 0) return t("home.week.streak.none");
  return days === 1 ? t("home.week.streak.one") : t("home.week.streak.many", { count: days });
}

function tasksText(done: number, total: number): string {
  return done === 1
    ? t("home.week.tasks.one", { total })
    : t("home.week.tasks.many", { done, total });
}

/** The week's progress: bar and text « 3 h 10 sur 5 h prévues », tasks done and streak. */
export function WeekCard({ week, unavailable = false }: WeekCardProps) {
  const planned = week?.plannedMinutes ?? 0;
  const share = week && planned > 0 ? Math.min(1, week.doneMinutes / planned) : 0;
  return (
    <section
      aria-labelledby="home-week"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-week" className="text-lg font-medium">
        {t("home.week.title")}
      </h2>
      {unavailable ? (
        <p className="text-muted-foreground">{t("home.unavailable")}</p>
      ) : week === null ? (
        <p className="text-muted-foreground">{t("home.week.none")}</p>
      ) : planned === 0 ? (
        <p className="text-muted-foreground">{t("home.week.nothingPlanned")}</p>
      ) : (
        <>
          <div
            role="progressbar"
            aria-label={t("home.week.progressLabel")}
            aria-valuemin={0}
            aria-valuemax={planned}
            aria-valuenow={Math.min(week.doneMinutes, planned)}
            aria-valuetext={t("home.week.time", {
              done: formatMinutes(week.doneMinutes),
              planned: formatMinutes(planned),
            })}
            className="h-2 w-full overflow-hidden rounded-full bg-muted"
          >
            <div className="h-full rounded-full bg-primary" style={{ width: `${share * 100}%` }} />
          </div>
          <p className="tabular-nums">
            {t("home.week.time", {
              done: formatMinutes(week.doneMinutes),
              planned: formatMinutes(planned),
            })}
          </p>
        </>
      )}
      {week && !unavailable ? (
        <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
          <li>{tasksText(week.tasksDone, week.tasksTotal)}</li>
          <li>{streakText(week.streakDays)}</li>
        </ul>
      ) : null}
    </section>
  );
}
