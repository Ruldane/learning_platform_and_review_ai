import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";

interface LessonNavProps {
  lessonId: string;
  /** A ready lesson can be studied with the tutor. */
  ready: boolean;
}

/** Back to the lesson list, and « Étudier cette leçon » (guided session on this lesson). */
export function LessonNav({ lessonId, ready }: LessonNavProps) {
  return (
    <nav className="flex flex-wrap items-center justify-between gap-3">
      <Link to="/learn/lessons" className="text-sm underline underline-offset-2">
        {t("lessons.page.back")}
      </Link>
      {ready ? (
        <Link
          to={`/study/session?lesson=${lessonId}`}
          className={buttonVariants({ variant: "outline" })}
        >
          {t("lessons.page.study")}
        </Link>
      ) : null}
    </nav>
  );
}
