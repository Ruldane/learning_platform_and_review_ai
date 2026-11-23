import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export type TrainingLessonOption = { id: string; title: string };

export function ChosenLessons({
  ids,
  lessons,
  busy,
  onChange,
}: {
  ids: string[];
  lessons: TrainingLessonOption[];
  busy: boolean;
  onChange?: (ids: string[]) => void;
}) {
  return (
    <ul className="grid gap-1">
      {ids.map((id, index) => {
        const title =
          lessons.find((lesson) => lesson.id === id)?.title ??
          t("training.lessonUnavailable", { number: index + 1 });
        return (
          <li key={id} className="flex flex-wrap items-center justify-between gap-1 text-sm">
            {title}
            {onChange && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={busy}
                aria-label={t("training.removeLesson", { title })}
                onClick={() => onChange(ids.filter((lesson) => lesson !== id))}
              >
                {t("training.remove")}
              </Button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
