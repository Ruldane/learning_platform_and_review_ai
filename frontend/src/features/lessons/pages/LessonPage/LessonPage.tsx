import type { ComponentType } from "react";
import { useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { LessonVerification } from "../../components/LessonVerification";
import { useLesson } from "../../hooks/useLesson";
import { useResourceStatus } from "../../hooks/useResourceStatus";
import { LessonNav } from "./LessonNav";
import { LessonPreparing } from "./LessonPreparing";
import { PublishedLesson, type LessonConversationPanelProps } from "./PublishedLesson";

export interface LessonUpdatesPanelProps {
  lessonId: string;
  onPublication: () => void;
}

interface LessonPageProps {
  updatesPanel?: ComponentType<LessonUpdatesPanelProps>;
  conversationPanel?: ComponentType<LessonConversationPanelProps>;
}

/**
 * Leçon (`/learn/lessons/:lessonId`) : le lecteur, les ressources du module et le PDF quand la
 * leçon est prête ; sinon l'état de sa préparation, dit clairement.
 */
export function LessonPage({ conversationPanel, updatesPanel: Updates }: LessonPageProps) {
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
  const published = data.status === "ready";
  const checking = Boolean(data.verification_session_id);
  const verification =
    checking || data.verification_failure_reason ? (
      <LessonVerification
        published={published}
        checking={checking}
        failure={data.verification_failure_reason}
      />
    ) : null;
  return (
    <div className="flex flex-col gap-6">
      <LessonNav lessonId={data.id} ready={published} />
      {published ? (
        <>
          {verification}
          {Updates && <Updates lessonId={data.id} onPublication={() => void lesson.refetch()} />}
          <PublishedLesson
            key={data.id}
            lesson={data}
            resources={resources}
            conversationPanel={conversationPanel}
          />
        </>
      ) : (
        <>
          <header>
            <h1 className="text-2xl font-semibold">{data.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("lessons.page.week", { rank: data.week_rank })}
            </p>
          </header>
          {verification ?? <LessonPreparing lesson={data} />}
        </>
      )}
    </div>
  );
}
