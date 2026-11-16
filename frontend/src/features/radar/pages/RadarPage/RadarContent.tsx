import type { UseQueryResult } from "@tanstack/react-query";
import { useLocation } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRadarRun } from "../../hooks/useRadarRun";
import type { useStartRadar } from "../../hooks/useStartRadar";
import type { HistoryItemView, LatestView } from "../../toView";
import { RadarHistory } from "./RadarHistory";
import { RadarLaunch } from "./RadarLaunch";
import { RunArea } from "./RunArea";
import { useLaunch } from "./useLaunch";

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
  const launched = launchState(useLocation().state);
  const detail = useRadarRun(runId, launched.sessionId, createSocket);
  const view = runId ? detail.query.data : latest.latest;
  const onRun = useLaunch(starter, runId, view?.id);
  const waiting = runId !== null && detail.query.isPending;
  const running =
    starter.pending || waiting || latest.runningId !== null || view?.status === "running";

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
      <RunArea
        byAddress={runId !== null}
        view={view}
        detail={detail}
        focusRun={launched.sessionId !== null || launched.resumed}
      />
      <RadarHistory history={history} currentId={view?.id ?? null} />
    </div>
  );
}
