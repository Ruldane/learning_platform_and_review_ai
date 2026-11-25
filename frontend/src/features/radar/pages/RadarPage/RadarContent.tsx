import type { UseQueryResult } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRadarRun } from "../../hooks/useRadarRun";
import type { StartedRun, useStartRadar } from "../../hooks/useStartRadar";
import type { HistoryItemView, LatestView } from "../../toView";
import { RadarHistory } from "./RadarHistory";
import { RadarLaunch } from "./RadarLaunch";
import { RunArea } from "./RunArea";
import { useLaunch } from "./useLaunch";
import { useLaunchFocus } from "./useLaunchFocus";

/**
 * The page's launch, if it concerns the sweep shown; otherwise nothing: this one was not
 * launched here.
 */
function launchOf(started: StartedRun | null, runId: string | null) {
  const mine = started !== null && started.runId === runId ? started : null;
  return { sessionId: mine?.sessionId ?? null, resumed: mine?.resumed ?? false };
}

interface RadarContentProps {
  /** The sweep in the address, or `null` for the latest finished sweep. */
  runId: string | null;
  latest: LatestView;
  history: UseQueryResult<HistoryItemView[]>;
  starter: ReturnType<typeof useStartRadar>;
  createSocket?: SocketFactory;
}

/** The page once `GET /radar/latest` is read: launch, sweep shown, history. */
export function RadarContent({ runId, latest, history, starter, createSocket }: RadarContentProps) {
  // What this page's launch gave to follow (the 202 session, or a resumed sweep):
  // it comes from the page's store, never from browser history (reload, back).
  const launched = launchOf(starter.started, runId);
  const detail = useRadarRun(runId, launched.sessionId, createSocket);
  const view = runId ? detail.query.data : latest.latest;
  const onRun = useLaunch(starter, runId, view?.id);
  const waiting = runId !== null && detail.query.isPending;
  const running =
    starter.pending || waiting || latest.runningId !== null || view?.status === "running";
  const focusRun = useLaunchFocus(starter.started, runId, view?.status === "running");

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
        launchMenu={starter.launchMenu}
      />
      {launched.resumed && view?.status === "running" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("radar.page.resumed")}
        </p>
      ) : null}
      <RunArea byAddress={runId !== null} view={view} detail={detail} focusRun={focusRun} />
      <RadarHistory history={history} currentId={view?.id ?? null} />
    </div>
  );
}
