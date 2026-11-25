import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { LessonSummaryOut } from "../../types";
import { LessonTaskProgress } from "./LessonTaskProgress";

/**
 * A lesson in the list: its title (link to the reader), its state, its length and its
 * progress in the program (« Terminée » when all the module's tasks are done).
 */
export function LessonRow({ lesson }: { lesson: LessonSummaryOut }) {
  const ready = lesson.status === "ready";
  const status = lesson.verification_session_id ? "verifying" : lesson.status;
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-2 rounded-xl border bg-card px-4 py-3">
      <Link
        to={`/learn/lessons/${lesson.id}`}
        aria-label={t("lessons.list.open", { title: lesson.title })}
        className="min-w-0 font-medium break-words underline underline-offset-2"
      >
        {lesson.title}
      </Link>
      <span className="flex flex-wrap items-baseline gap-3 text-sm">
        {ready ? (
          <span className="text-muted-foreground">
            {t("lessons.list.words", { count: lesson.word_count.toLocaleString("en-GB") })}
          </span>
        ) : null}
        <span className={cn("font-medium", ready ? "text-primary" : "text-muted-foreground")}>
          {t(`lessons.status.${status}`)}
        </span>
        <LessonTaskProgress lesson={lesson} />
      </span>
    </li>
  );
}
