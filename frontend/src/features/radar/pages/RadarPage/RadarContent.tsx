import type { UseQueryResult } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import type { RadarRunRequestView } from "../../components/viewTypes";
import { useRadarRun } from "../../hooks/useRadarRun";
import type { useStartRadar } from "../../hooks/useStartRadar";
import type { HistoryItemView, LatestView } from "../../toView";
import { RadarHistory } from "./RadarHistory";
import { RadarLaunch } from "./RadarLaunch";
import { RunArea } from "./RunArea";

/** Ce que le lancement a laissé dans l'état de navigation : la session du 202, ou un relevé repris. */
function launchState(state: unknown): { sessionId: string | null; resumed: boolean } {
  const value =
    typeof state === "object" && state !== null ? (state as Record<string, unknown>) : {};
  return {
    sessionId: typeof value.sessionId === "string" ? value.sessionId : null,
    resumed: value.resumed === true,
  };
}

interface RadarContentProps {
  /** Le relevé de l'adresse, ou `null` pour le dernier relevé fini. */
  runId: string | null;
  latest: LatestView;
  history: UseQueryResult<HistoryItemView[]>;
  starter: ReturnType<typeof useStartRadar>;
  createSocket?: SocketFactory;
}

/** La page une fois `GET /radar/latest` lu : lancement, relevé montré, historique. */
export function RadarContent({ runId, latest, history, starter, createSocket }: RadarContentProps) {
  const navigate = useNavigate();
  const launched = launchState(useLocation().state);
  const detail = useRadarRun(runId, launched.sessionId, createSocket);
  const view = runId ? detail.query.data : latest.latest;
  // Un lancement tient du clic jusqu'à ce que le relevé à suivre soit lu : un second clic (double
  // clic, Entrée répétée) n'envoie rien, il ne peut donc pas produire un 409 qui écraserait la
  // session du 202.
  const launching = useRef(false);
  const viewedId = view?.id;
  useEffect(() => {
    if (runId !== null && viewedId === runId) launching.current = false;
  }, [runId, viewedId]);
  const waiting = runId !== null && detail.query.isPending;
  const running =
    starter.pending || waiting || latest.runningId !== null || view?.status === "running";

  const onRun = (request: RadarRunRequestView) => {
    if (launching.current) return;
    launching.current = true;
    void starter.start(request).then((started) => {
      if (!started) {
        launching.current = false;
        return;
      }
      void navigate(`/carriere/radar/${started.runId}`, {
        state: { sessionId: started.sessionId, resumed: started.resumed },
      });
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t("radar.page.title")}</h1>
        <p className="text-muted-foreground">{t("radar.page.intro")}</p>
      </header>
      <RadarLaunch
        defaults={latest.defaults}
        running={running}
        errors={starter.errors}
        onRun={onRun}
      />
      {launched.resumed && view?.status === "running" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("radar.page.resumed")}
        </p>
      ) : null}
      <RunArea byAddress={runId !== null} view={view} detail={detail} />
      <RadarHistory history={history} currentId={view?.id ?? null} />
    </div>
  );
}
