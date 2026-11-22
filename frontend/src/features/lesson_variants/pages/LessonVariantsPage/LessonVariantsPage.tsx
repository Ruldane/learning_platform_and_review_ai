import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { VariantPicker } from "../../components/VariantPicker";
import { VariantReading } from "../../components/VariantReading";
import { VariantHistory } from "../VariantHistory";
import { useLessonVariants } from "./useLessonVariants";

export function LessonVariantsPage() {
  const view = useLessonVariants();
  const error = [view.programs, view.lessons, view.history, view.edition, view.prepare]
    .find((query) => query.error)?.error;
  return (
    <section className="flex max-w-4xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("lessonVariants.title")}</h1>
      <p className="text-muted-foreground">{t("lessonVariants.intro")}</p>
      <VariantPicker programs={view.programs.data ?? []} lessons={view.lessons.data ?? []}
        programId={view.programId} lessonId={view.lessonId} busy={view.prepare.isPending}
        onProgram={view.setProgramId} onLesson={view.setLessonId}
        onPrepare={() => { if (view.lessonId) view.prepare.mutate(view.lessonId); }} />
      {error && <InlineError message={errorMessage(error)} />}
      {(view.history.isPending || view.edition.isFetching || view.prepare.isPending) && <LoadingState />}
      {view.edition.data && (
        <>
          <VariantReading edition={view.edition.data} format={view.format} onFormat={view.setFormat} />
          <Link className="w-fit underline" to={`/apprendre/lecons/${view.edition.data.lesson_id}`}>
            {t("lessonVariants.openSource")}
          </Link>
        </>
      )}
      {view.history.data && <VariantHistory editions={view.history.data} currentId={view.editionId} />}
    </section>
  );
}
