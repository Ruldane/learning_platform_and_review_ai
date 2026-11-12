import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { LessonSummaryOut } from "../../types";

/** Une leçon de la liste : son titre (lien vers le lecteur), son état et sa longueur. */
export function LessonRow({ lesson }: { lesson: LessonSummaryOut }) {
  const ready = lesson.status === "ready";
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-2 rounded-xl border bg-card px-4 py-3">
      <Link
        to={`/apprendre/lecons/${lesson.id}`}
        aria-label={t("lessons.list.open", { title: lesson.title })}
        className="min-w-0 font-medium break-words underline underline-offset-2"
      >
        {lesson.title}
      </Link>
      <span className="flex items-baseline gap-3 text-sm">
        {ready ? (
          <span className="text-muted-foreground">
            {t("lessons.list.words", { count: lesson.word_count.toLocaleString("fr-FR") })}
          </span>
        ) : null}
        <span className={cn("font-medium", ready ? "text-primary" : "text-muted-foreground")}>
          {t(`lessons.status.${lesson.status}`)}
        </span>
      </span>
    </li>
  );
}
