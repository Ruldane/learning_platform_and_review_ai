import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";

interface LessonNavProps {
  lessonId: string;
  /** Une leçon prête peut être étudiée avec le tuteur. */
  ready: boolean;
}

/** Retour à la liste des leçons, et « Étudier cette leçon » (session guidée sur cette leçon). */
export function LessonNav({ lessonId, ready }: LessonNavProps) {
  return (
    <nav className="flex flex-wrap items-center justify-between gap-3">
      <Link to="/apprendre/lecons" className="text-sm underline underline-offset-2">
        {t("lessons.page.back")}
      </Link>
      {ready ? (
        <Link
          to={`/etudier/session?lecon=${lessonId}`}
          className={buttonVariants({ variant: "outline" })}
        >
          {t("lessons.page.study")}
        </Link>
      ) : null}
    </nav>
  );
}
