import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { TrainingLessonOption } from "./ChosenLessons";

export function AddTrainingLesson({
  lessons,
  busy,
  onAdd,
}: {
  lessons: TrainingLessonOption[];
  busy: boolean;
  onAdd: (id: string) => void;
}) {
  const id = useId();
  return (
    <>
      <label htmlFor={id} className="text-sm">
        {t("training.addLesson")}
      </label>
      <select
        id={id}
        className={fieldClass}
        value=""
        disabled={busy}
        onChange={(event) => onAdd(event.target.value)}
      >
        <option value="" disabled>
          {t("training.chooseLesson")}
        </option>
        {lessons.map((lesson) => (
          <option key={lesson.id} value={lesson.id}>
            {lesson.title}
          </option>
        ))}
      </select>
    </>
  );
}
