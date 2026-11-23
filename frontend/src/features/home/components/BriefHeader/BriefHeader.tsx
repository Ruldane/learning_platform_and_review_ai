import { longDay } from "@/shared/lib/format";
import { clockTime } from "@/shared/lib/relativeTime";
import { t } from "@/shared/i18n/t";

interface BriefHeaderProps {
  /** Le jour local du brief, `AAAA-MM-JJ`. */
  day: string;
  /** L'instant ISO où le brief a été préparé. */
  generatedAt: string;
}

/** Le titre de l'accueil : « Ton brief du jour », le jour en toutes lettres et l'heure de préparation. */
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
