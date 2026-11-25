import { useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useProgram } from "../../hooks/useProgram";
import { ProgramScreen } from "./ProgramScreen";

/**
 * Program (`/learn/programs/:programId`): week as calendar, full list,
 * progress; a draft is validated or revised here (breakpoint no. 3).
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
