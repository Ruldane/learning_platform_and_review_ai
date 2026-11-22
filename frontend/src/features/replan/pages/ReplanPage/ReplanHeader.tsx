import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

export function ReplanHeader({ programId }: { programId: string }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold">{t("replan.title")}</h1>
      <div className="flex flex-wrap gap-3 text-sm">
        <Link to={`/apprendre/programme/${programId}`} className="underline">
          {t("replan.back")}
        </Link>
        <Link
          to={`/reglages/agenda?programme=${encodeURIComponent(programId)}`}
          className="underline"
        >
          {t("calendar.link")}
        </Link>
      </div>
    </header>
  );
}
