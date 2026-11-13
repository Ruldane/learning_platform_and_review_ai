import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { VersionHistory } from "../../components/VersionHistory";
import type { VersionView } from "../../components/viewTypes";

interface ReplanHistoryProps {
  programId: string;
  versions: VersionView[] | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
}

/** L'historique des versions du plan avec son chargement et son erreur. */
export function ReplanHistory(props: ReplanHistoryProps) {
  const { programId, versions, loading, error, onRetry } = props;
  const navigate = useNavigate();
  const toProgram = {
    label: t("replan.history.emptyAction"),
    onClick: () => void navigate(`/apprendre/programme/${programId}`),
  };
  return (
    <section aria-labelledby="replan-history-title" className="flex flex-col gap-2">
      <h2 id="replan-history-title" className="text-lg font-semibold">
        {t("replan.history.heading")}
      </h2>
      {versions ? <VersionHistory versions={versions} emptyAction={toProgram} /> : null}
      {!versions && loading ? <LoadingState /> : null}
      {!versions && !loading && error ? (
        <ErrorState message={errorMessage(error)} onRetry={onRetry} />
      ) : null}
    </section>
  );
}
