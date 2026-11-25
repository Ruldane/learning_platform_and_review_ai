import { useNavigate, useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ProgramPicker } from "../../components/ProgramPicker";
import { usePrograms } from "../../hooks/usePrograms";
import { LessonsBody } from "./LessonsBody";

/**
 * Lessons (`/learn/lessons`): a program's lessons, by week, with their state (upcoming,
 * being prepared, ready, new attempt planned) and their progress. The newest by default;
 * with several programs, a dropdown picks one (`?program=<id>`).
 */
export function LessonsPage() {
  const navigate = useNavigate();
  const programs = usePrograms();
  const [params, setParams] = useSearchParams();
  const list = programs.data ?? [];
  const selectedId = params.get("program") ?? params.get("programme");
  const chosen = list.find((program) => program.id === selectedId) ?? list[0];

  let body;
  if (programs.isPending) {
    body = <LoadingState label={t("lessons.list.loading")} />;
  } else if (programs.isError) {
    body = (
      <ErrorState message={errorMessage(programs.error)} onRetry={() => void programs.refetch()} />
    );
  } else if (chosen) {
    body = <LessonsBody key={chosen.id} programId={chosen.id} />;
  } else {
    body = (
      <EmptyState
        title={t("lessons.list.noProgramTitle")}
        description={t("lessons.list.noProgramDescription")}
        action={{
          label: t("lessons.list.noProgramAction"),
          onClick: () => void navigate("/learn/council"),
        }}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{t("lessons.list.title")}</h1>
          <p className="mt-2 text-muted-foreground">{t("lessons.list.intro")}</p>
        </div>
        {chosen && list.length > 1 ? (
          <ProgramPicker
            programs={list.map(({ id, title }) => ({ id, title }))}
            value={chosen.id}
            onChange={(program) => setParams({ program }, { replace: true })}
          />
        ) : null}
      </header>
      {body}
    </div>
  );
}
