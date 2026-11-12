import { t } from "@/shared/i18n/t";
import type { LessonSummaryOut } from "../../types";
import { LessonRow } from "./LessonRow";

/** Les leçons d'un programme groupées par semaine, dans l'ordre du programme. */
export function LessonsList({ lessons }: { lessons: LessonSummaryOut[] }) {
  const ranks = [...new Set(lessons.map((lesson) => lesson.week_rank))];
  return (
    <div className="flex flex-col gap-5">
      {ranks.map((rank) => (
        <section
          key={rank}
          aria-labelledby={`lessons-week-${rank}`}
          className="flex flex-col gap-2"
        >
          <h2 id={`lessons-week-${rank}`} className="text-lg font-semibold">
            {t("lessons.list.weekGroup", { rank })}
          </h2>
          <ul className="flex flex-col gap-2">
            {lessons
              .filter((lesson) => lesson.week_rank === rank)
              .map((lesson) => (
                <LessonRow key={lesson.id} lesson={lesson} />
              ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
