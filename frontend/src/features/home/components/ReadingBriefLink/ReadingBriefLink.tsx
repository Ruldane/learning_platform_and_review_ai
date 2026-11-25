import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

export function ReadingBriefLink({ count }: { count: number }) {
  return (
    <Link
      to="/memory/reading"
      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-card p-4"
    >
      <span className="font-medium underline underline-offset-4">{t("reading.inBrief")}</span>
      <span className="text-sm text-muted-foreground">
        {count === 0 ? t("home.readingEmpty") : count === 1 ? t("reading.countOne") : t("reading.count", { count })}
      </span>
    </Link>
  );
}
