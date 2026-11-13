import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { VersionHistory } from "../../components/VersionHistory";
import type { VersionView } from "../../components/viewTypes";

interface ReplanHistoryProps {
  versions: VersionView[] | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
}

/** L'historique des versions du plan avec son chargement et son erreur. */
export function ReplanHistory({ versions, loading, error, onRetry }: ReplanHistoryProps) {
  return (
    <section aria-labelledby="replan-history-title" className="flex flex-col gap-2">
      <h2 id="replan-history-title" className="text-lg font-semibold">
        {t("replan.history.heading")}
      </h2>
      {versions ? <VersionHistory versions={versions} /> : null}
      {!versions && loading ? <LoadingState /> : null}
      {!versions && !loading && error ? (
        <ErrorState message={errorMessage(error)} onRetry={onRetry} />
      ) : null}
    </section>
  );
}
