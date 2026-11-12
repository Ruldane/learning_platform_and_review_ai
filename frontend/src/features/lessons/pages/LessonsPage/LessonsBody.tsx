import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useProgramLessons } from "../../hooks/useProgramLessons";
import { LessonsList } from "./LessonsList";

/** Les leçons du programme `programId` : chargement, erreur, rien encore (avec une issue) ou la liste. */
export function LessonsBody({ programId }: { programId: string }) {
  const navigate = useNavigate();
  const lessons = useProgramLessons(programId);
  if (lessons.isPending) return <LoadingState label={t("lessons.list.loading")} />;
  if (lessons.isError) {
    return (
      <ErrorState message={errorMessage(lessons.error)} onRetry={() => void lessons.refetch()} />
    );
  }
  if (lessons.data.length === 0) {
    return (
      <EmptyState
        title={t("lessons.list.emptyTitle")}
        description={t("lessons.list.emptyDescription")}
        action={{
          label: t("lessons.list.emptyAction"),
          onClick: () => void navigate(`/apprendre/programme/${programId}`),
        }}
      />
    );
  }
  return <LessonsList lessons={lessons.data} />;
}
