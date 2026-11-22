import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import type { ChapterView } from "../viewTypes";

export function Chapters({ items }: { items: ChapterView[] }) {
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="projection-recommendations" className="grid gap-3">
      <h2 id="projection-recommendations" className="text-xl font-semibold">
        {t("futureSelf.recommendations")}
      </h2>
      <ul className="grid gap-2">
        {items.map((chapter) => (
          <li key={chapter.id} className="rounded-lg border bg-card p-3">
            <Link
              to={chapter.link}
              className="font-medium underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
            >
              {chapter.title}
            </Link>
            <p className="text-sm text-muted-foreground">
              {formatMinutes(chapter.minutes)} ·{" "}
              {t("futureSelf.impact", { unlocked: chapter.unlocked, improved: chapter.improved })}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
