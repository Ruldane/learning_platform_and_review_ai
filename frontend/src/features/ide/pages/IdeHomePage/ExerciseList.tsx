import { useId } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { ExerciseView } from "../../components/viewTypes";
import { ExerciseRow } from "./ExerciseRow";

interface ExerciseListProps {
  exercises: ExerciseView[];
  loading: boolean;
  error: unknown;
  busy: boolean;
  onRetry: () => void;
  onOpen: (exercise: ExerciseView) => void;
}

/** The exercises list with their state; loading and failure are announced, the rest stays. */
export function ExerciseList({
  exercises,
  loading,
  error,
  busy,
  onRetry,
  onOpen,
}: ExerciseListProps) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <h2 id={headingId} className="text-lg font-medium">
        {t("ide.home.exercises")}
      </h2>
      {loading ? <LoadingState label={t("ide.home.loading")} /> : null}
      {error ? <ErrorState message={errorMessage(error)} onRetry={onRetry} /> : null}
      {!loading && !error && exercises.length === 0 ? (
        <p className="text-muted-foreground">{t("ide.home.empty")}</p>
      ) : null}
      <ul className="flex flex-col gap-3">
        {exercises.map((exercise) => (
          <li key={exercise.id}>
            <ExerciseRow exercise={exercise} busy={busy} onOpen={onOpen} />
          </li>
        ))}
      </ul>
    </section>
  );
}
