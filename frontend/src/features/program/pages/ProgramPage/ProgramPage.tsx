import { useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useProgram } from "../../hooks/useProgram";
import { ProgramScreen } from "./ProgramScreen";

/**
 * Programme (`/apprendre/programme/:programId`) : semaine en calendrier, liste complète,
 * avancement ; un brouillon se valide ou se révise ici (point d'arrêt n° 3).
 */
export function ProgramPage() {
  const { programId = "" } = useParams();
  const program = useProgram(programId);
  if (program.isPending) return <LoadingState label={t("program.page.loading")} />;
  if (program.isError) {
    return (
      <ErrorState message={errorMessage(program.error)} onRetry={() => void program.refetch()} />
    );
  }
  return <ProgramScreen program={program.data} />;
}
