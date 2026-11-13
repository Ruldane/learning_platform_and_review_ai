import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useLessonTitle } from "../../hooks/useLessonTitle";
import type { ChosenLesson } from "./chosenLesson";

interface ChosenLessonCardProps {
  chosen: ChosenLesson;
  disabled: boolean;
  onStart: () => void;
}

/**
 * La leçon choisie à la place du bloc du jour : son titre, le passage sur lequel le tuteur est
 * interrogé s'il y en a un, et le bouton de départ. Les tâches du bloc ne sont pas cochées.
 */
export function ChosenLessonCard({ chosen, disabled, onStart }: ChosenLessonCardProps) {
  const lesson = useLessonTitle(chosen.lessonId);
  if (lesson.isPending) return <LoadingState label={t("study.home.chosen.loading")} />;
  if (lesson.isError) {
    return (
      <ErrorState message={errorMessage(lesson.error)} onRetry={() => void lesson.refetch()} />
    );
  }
  return (
    <section className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {t("study.home.chosen.label")}
      </p>
      <h2 className="text-lg font-semibold">{lesson.data.title}</h2>
      {chosen.question ? (
        <figure className="flex flex-col gap-1">
          <figcaption className="text-sm font-medium">{t("study.home.chosen.question")}</figcaption>
          <blockquote className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg border-l-4 border-primary bg-muted px-3 py-2 text-sm">
            {chosen.question}
          </blockquote>
        </figure>
      ) : null}
      <Button className="self-start" disabled={disabled} onClick={onStart}>
        {chosen.question ? t("study.home.chosen.ask") : t("study.home.chosen.start")}
      </Button>
    </section>
  );
}
