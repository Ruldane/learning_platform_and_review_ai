import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { useRadarRun } from "../../hooks/useRadarRun";
import type { RunView } from "../../toView";
import { RunSection } from "./RunSection";

interface RunAreaProps {
  /** The sweep comes from the address (`/career/radar/:runId`), not the latest finished sweep. */
  byAddress: boolean;
  view: RunView | null | undefined;
  detail: ReturnType<typeof useRadarRun>;
  /** A launch has just led here: the sweep's tracker takes the button's focus. */
  focusRun?: boolean;
}

/** The sweep shown, or what stands in for it: loading, sweep not found, error, nothing yet. */
export function RunArea({ byAddress, view, detail, focusRun = false }: RunAreaProps) {
  const navigate = useNavigate();
  const { query } = detail;
  if (view) return <RunSection view={view} follow={detail} focusOnMount={focusRun} />;
  if (!byAddress) {
    return (
      <EmptyState title={t("radar.page.emptyTitle")} description={t("radar.page.emptyText")} />
    );
  }
  if (query.isPending) return <LoadingState label={t("radar.page.loadingRun")} />;
  if (detail.missing) {
    return (
      <EmptyState
        title={t("radar.page.notFoundTitle")}
        description={t("radar.page.notFoundText")}
        action={{
          label: t("radar.page.notFoundAction"),
          onClick: () => void navigate("/career/radar"),
        }}
      />
    );
  }
  return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
}
