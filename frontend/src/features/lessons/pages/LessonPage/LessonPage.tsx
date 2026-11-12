import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { LessonReader } from "../../components/LessonReader";
import { ResourceList } from "../../components/ResourceList";
import { useLesson } from "../../hooks/useLesson";
import { useResourceStatus } from "../../hooks/useResourceStatus";
import { toLessonView, toResourceView } from "../../toView";
import { LessonPreparing } from "./LessonPreparing";

/**
 * Leçon (`/apprendre/lecons/:lessonId`) : le lecteur, les ressources du module et le PDF quand la
 * leçon est prête ; sinon l'état de sa préparation, dit clairement.
 */
export function LessonPage() {
  const { lessonId = "" } = useParams();
  const lesson = useLesson(lessonId);
  const resources = useResourceStatus();

  if (lesson.isPending) return <LoadingState label={t("lessons.page.loading")} />;
  if (lesson.isError) {
    return (
      <ErrorState message={errorMessage(lesson.error)} onRetry={() => void lesson.refetch()} />
    );
  }
  const { data } = lesson;
  return (
    <div className="flex flex-col gap-6">
      <nav>
        <Link to="/apprendre/lecons" className="text-sm underline underline-offset-2">
          {t("lessons.page.back")}
        </Link>
      </nav>
      {data.status === "ready" ? (
        <>
          <LessonReader lesson={toLessonView(data)} />
          <section aria-labelledby="lesson-resources-title" className="flex flex-col gap-3">
            <h2 id="lesson-resources-title" className="text-xl font-semibold">
              {t("lessons.resources.heading")}
            </h2>
            {resources.error ? <InlineError message={resources.error} /> : null}
            {data.resources.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("lessons.resources.empty")}</p>
            ) : (
              <ResourceList
                resources={data.resources.map(toResourceView)}
                onToggleStatus={resources.setStatus}
              />
            )}
          </section>
        </>
      ) : (
        <>
          <header>
            <h1 className="text-2xl font-semibold">{data.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("lessons.page.week", { rank: data.week_rank })}
            </p>
          </header>
          <LessonPreparing lesson={data} />
        </>
      )}
    </div>
  );
}
