import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { StudyModeView } from "../../components/viewTypes";
import { useStartStudy } from "../../hooks/useStartStudy";
import { useStudySummary } from "../../hooks/useStudySummary";
import { ChosenStart } from "./ChosenStart";
import { DayStart } from "./DayStart";
import { useChosenLesson } from "./chosenLesson";

/**
 * Session guidée (`/etudier/session`) : le bloc du jour, ou la leçon choisie (`?lecon=` et
 * « Demander au tuteur » depuis une leçon), le mode du tuteur, et la reprise d'une session ouverte.
 */
export function StudyHomePage() {
  const summary = useStudySummary();
  const chosen = useChosenLesson();
  const starter = useStartStudy();
  const [picked, setPicked] = useState<StudyModeView | null>(null);
  // Une question sur un passage se pose en mode direct, tant que le mode n'a pas été choisi.
  const mode = picked ?? (chosen?.question ? "direct" : "socratic");
  const common = { mode, onMode: setPicked, starter };

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold">{t("study.home.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("study.home.intro")}</p>
      </header>
      {summary.isPending ? <LoadingState label={t("study.home.loading")} /> : null}
      {summary.isError ? (
        <ErrorState message={errorMessage(summary.error)} onRetry={() => void summary.refetch()} />
      ) : null}
      {starter.error ? <InlineError message={starter.error} /> : null}
      {summary.data && chosen ? (
        <ChosenStart {...common} chosen={chosen} openSessionId={summary.data.open_session_id} />
      ) : null}
      {summary.data && !chosen ? (
        <DayStart
          {...common}
          block={summary.data.block}
          openSessionId={summary.data.open_session_id}
        />
      ) : null}
    </div>
  );
}
