import { Navigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useRadar } from "../../hooks/useRadar";
import { useStartRadar } from "../../hooks/useStartRadar";
import { RadarContent } from "./RadarContent";

const RADAR_PATH = "/carriere/radar";

/**
 * Le radar du marché (`/carriere/radar`, `/carriere/radar/:runId`) : le formulaire prérempli, le
 * relevé montré (le dernier fini, ou celui de l'adresse ; en cours, suivi par sa session), puis
 * l'historique. Un relevé déjà en cours est suivi, jamais relancé. `createSocket` ne sert qu'aux
 * tests.
 */
export function RadarPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { runId = null } = useParams();
  const { latest, history } = useRadar();
  const starter = useStartRadar();
  if (latest.data) {
    // Sans relevé choisi, l'adresse du radar suit celui qui tourne, sauf si un lancement vient de
    // désigner le relevé à suivre : sa navigation porte la session du 202.
    if (runId === null && latest.data.runningId && !starter.started) {
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
