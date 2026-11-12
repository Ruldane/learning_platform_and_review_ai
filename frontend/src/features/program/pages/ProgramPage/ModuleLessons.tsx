import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { ModuleLessonView } from "../../types";

interface ModuleLessonsProps {
  lessons: ModuleLessonView[];
}

/** Les leçons du programme, une par module : leur état et le lien pour les lire. */
export function ModuleLessons({ lessons }: ModuleLessonsProps) {
  if (lessons.length === 0) return null;
  return (
    <section aria-labelledby="program-lessons-title" className="flex flex-col gap-3">
      <h2 id="program-lessons-title" className="text-lg font-semibold">
        {t("program.lessons.heading")}
      </h2>
      <ul className="flex flex-col gap-2">
        {lessons.map((lesson) => (
          <li
            key={lesson.moduleId}
            className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border bg-card px-3 py-2"
          >
            <span className="font-medium">{lesson.moduleTitle}</span>
            <span className="flex items-baseline gap-3 text-sm">
              <span className="text-muted-foreground">
                {lesson.status
                  ? t(`lessons.status.${lesson.status}`)
                  : t("program.lessons.waiting")}
              </span>
              {lesson.lessonId ? (
                <Link
                  to={`/apprendre/lecons/${lesson.lessonId}`}
                  className="underline underline-offset-2"
                >
                  {t("program.lessons.open")}
                  <span className="sr-only"> : {lesson.moduleTitle}</span>
                </Link>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
