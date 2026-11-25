import { Navigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useRadar } from "../../hooks/useRadar";
import { useStartRadar } from "../../hooks/useStartRadar";
import { RadarContent } from "./RadarContent";

const RADAR_PATH = "/career/radar";

/**
 * The market radar (`/career/radar`, `/career/radar/:runId`): the pre-filled form, the
 * sweep shown (the latest finished, or the one in the address; a running one is followed by its
 * session), then the history. A running sweep is followed, never relaunched. `createSocket`
 * tests.
 */
export function RadarPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { runId = null } = useParams();
  const { latest, history } = useRadar();
  const starter = useStartRadar();
  if (latest.data) {
    // With no sweep chosen, the radar address follows the one running, unless a launch has just
    // named that same sweep: its navigation carries the 202 session. Another sweep (the
    // Monday one) is followed.
    const justStarted = starter.started?.runId === latest.data.runningId;
    if (runId === null && latest.data.runningId && !justStarted) {
      return <Navigate to={`${RADAR_PATH}/${latest.data.runningId}`} replace />;
    }
    return (
      <RadarContent
        runId={runId}
        latest={latest.data}
        history={history}
        starter={starter}
        createSocket={createSocket}
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("radar.page.title")}</h1>
      {latest.isPending ? (
        <LoadingState label={t("radar.page.loading")} />
      ) : (
        <ErrorState message={errorMessage(latest.error)} onRetry={() => void latest.refetch()} />
      )}
    </div>
  );
}
