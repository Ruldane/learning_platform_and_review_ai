import { useNavigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { LessonReader } from "../../components/LessonReader";
import { useLesson } from "../../hooks/useLesson";
import { useResourceStatus } from "../../hooks/useResourceStatus";
import { toLessonView, toResourceView } from "../../toView";
import { LessonNav } from "./LessonNav";
import { LessonPreparing } from "./LessonPreparing";
import { LessonResources } from "./LessonResources";

/**
 * Leçon (`/apprendre/lecons/:lessonId`) : le lecteur, les ressources du module et le PDF quand la
 * leçon est prête ; sinon l'état de sa préparation, dit clairement.
 */
export function LessonPage() {
  const { lessonId = "" } = useParams();
  const lesson = useLesson(lessonId);
  const resources = useResourceStatus();
  const navigate = useNavigate();

  if (lesson.isPending) return <LoadingState label={t("lessons.page.loading")} />;
  if (lesson.isError) {
    return (
      <ErrorState message={errorMessage(lesson.error)} onRetry={() => void lesson.refetch()} />
    );
  }
  const { data } = lesson;
  return (
    <div className="flex flex-col gap-6">
      <LessonNav lessonId={data.id} ready={data.status === "ready"} />
      {data.status === "ready" ? (
        <>
          <LessonReader
            lesson={toLessonView(data)}
            onAskTutor={(passage) =>
              void navigate("/etudier/session", { state: { lessonId: data.id, question: passage } })
            }
          />
          <LessonResources resources={data.resources.map(toResourceView)} status={resources} />
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
