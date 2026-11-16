import { t } from "@/shared/i18n/t";
import type { Run } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { RunView } from "../../toView";
import { FailedRun } from "./FailedRun";
import { RunResult } from "./RunResult";

interface RunSectionProps {
  view: RunView;
  /** Le suivi de la session du relevé en cours (`null` tant qu'elle n'est pas retrouvée). */
  follow: { run: Run; sessionId: string | null };
}

/**
 * Le relevé montré : en cours, le fil de l'Éclaireur et de l'Analyste (le résultat arrive de la
 * lecture, jamais du fil) ; fini, son résultat ; en échec, la raison en clair.
 */
export function RunSection({ view, follow }: RunSectionProps) {
  if (view.status === "failed") return <FailedRun run={view} />;
  if (view.status === "done") return <RunResult run={view} />;
  return (
    <section aria-labelledby="radar-running" className="flex flex-col gap-3">
      <h2 id="radar-running" className="text-lg font-medium">
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
