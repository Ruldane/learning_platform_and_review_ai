import { t } from "@/shared/i18n/t";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";
import type { Run } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { RunView } from "../../toView";
import { FailedRun } from "./FailedRun";
import { RunResult } from "./RunResult";

interface RunSectionProps {
  view: RunView;
  /** Follow of the running sweep's session (`null` until it is found). */
  follow: { run: Run; sessionId: string | null };
  /** The sweep was just launched from the form: its title takes focus. */
  focusOnMount?: boolean;
}

/**
 * The sweep shown: while running, the Scout and Analyst thread (results come from the
 * read, never the thread); finished, its result; failed, the reason in plain words.
 */
export function RunSection({ view, follow, focusOnMount = false }: RunSectionProps) {
  const heading = useFocusOnMount<HTMLHeadingElement>(focusOnMount && view.status === "running");
  if (view.status === "failed") return <FailedRun run={view} />;
  if (view.status === "done") return <RunResult run={view} />;
  return (
    <section aria-labelledby="radar-running" className="flex flex-col gap-3">
      <h2
        id="radar-running"
        ref={heading}
        tabIndex={-1}
        className="text-lg font-medium outline-none"
      >
        {t("radar.page.runningTitle")}
      </h2>
      <p className="text-sm text-muted-foreground">{t("radar.page.runningText")}</p>
      {follow.sessionId ? (
        <RunFeed run={follow.run} label={t("radar.page.feed")} />
      ) : (
        <LoadingState label={t("radar.page.waitingSession")} />
      )}
    </section>
  );
}
