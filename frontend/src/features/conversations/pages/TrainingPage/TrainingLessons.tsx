import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { listTrainingLessons } from "../../trainingApi";
import { AddTrainingLesson } from "./AddTrainingLesson";
import { ChosenLessons } from "./ChosenLessons";

export function TrainingLessons({
  ids,
  busy,
  onChange,
}: {
  ids: string[];
  busy: boolean;
  onChange?: (ids: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const lessons = useQuery({
    queryKey: ["conversations", "training", "lessons"],
    queryFn: ({ signal }) => listTrainingLessons(signal),
    enabled: open,
  });
  const catalogue = lessons.data ?? [];
  const available = catalogue.filter((lesson) => !ids.includes(lesson.id));
  return (
    <details
      className="w-full rounded-lg border border-border p-3"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="cursor-pointer text-sm font-medium">
        {t("training.lessons", { count: ids.length })}
      </summary>
      {open ? (
        <div className="mt-3 flex flex-col gap-2">
          {lessons.isPending ? <p role="status">{t("training.lessonsLoading")}</p> : null}
          {lessons.isError ? <InlineError message={errorMessage(lessons.error)} /> : null}
          <ChosenLessons ids={ids} lessons={catalogue} busy={busy} onChange={onChange} />
          {onChange && ids.length < 8 && available.length > 0 && (
            <AddTrainingLesson
              lessons={available}
              busy={busy}
              onAdd={(id) => onChange([...ids, id])}
            />
          )}
          {lessons.isSuccess && catalogue.length === 0 && ids.length === 0 && (
            <p className="text-sm text-muted-foreground">{t("training.lessonsEmpty")}</p>
          )}
        </div>
      ) : null}
    </details>
  );
}
