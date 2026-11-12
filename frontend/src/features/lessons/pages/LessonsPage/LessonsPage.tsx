import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { usePrograms } from "../../hooks/usePrograms";
import { LessonsBody } from "./LessonsBody";

/**
 * Leçons (`/apprendre/lecons`) : les leçons du programme le plus récent, par semaine, avec leur
 * état (à venir, en préparation, prête, nouvelle tentative prévue).
 */
export function LessonsPage() {
  const navigate = useNavigate();
  const programs = usePrograms();
  const latest = programs.data?.[0];

  let body;
  if (programs.isPending) {
    body = <LoadingState label={t("lessons.list.loading")} />;
  } else if (programs.isError) {
    body = (
      <ErrorState message={errorMessage(programs.error)} onRetry={() => void programs.refetch()} />
    );
  } else if (latest) {
    body = <LessonsBody programId={latest.id} />;
  } else {
    body = (
      <EmptyState
        title={t("lessons.list.noProgramTitle")}
        description={t("lessons.list.noProgramDescription")}
        action={{
          label: t("lessons.list.noProgramAction"),
          onClick: () => void navigate("/apprendre/conseil"),
        }}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("lessons.list.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("lessons.list.intro")}</p>
      </header>
      {body}
    </div>
  );
}
