import { longDay } from "@/shared/lib/format";
import { clockTime } from "@/shared/lib/relativeTime";
import { t } from "@/shared/i18n/t";

interface BriefHeaderProps {
  /** The brief's local day, `YYYY-MM-DD`. */
  day: string;
  /** The ISO instant when the brief was prepared. */
  generatedAt: string;
}

/** The home title: « Ton brief du jour », the day spelled out and the preparation time. */
export function BriefHeader({ day, generatedAt }: BriefHeaderProps) {
  return (
    <header className="flex flex-col gap-1">
      <h1 className="text-2xl font-semibold">{t("home.brief.title")}</h1>
      <p className="text-muted-foreground">{t("home.brief.subtitle")}</p>
      <p className="text-muted-foreground">
        {longDay(day)}
        {" · "}
        {t("home.brief.preparedAt", { time: clockTime(generatedAt) })}
      </p>
    </header>
  );
}
