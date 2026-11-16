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
  /** Le suivi de la session du relevé en cours (`null` tant qu'elle n'est pas retrouvée). */
  follow: { run: Run; sessionId: string | null };
  /** Le relevé vient d'être lancé depuis le formulaire : son titre reprend le focus. */
  focusOnMount?: boolean;
}

/**
 * Le relevé montré : en cours, le fil de l'Éclaireur et de l'Analyste (le résultat arrive de la
 * lecture, jamais du fil) ; fini, son résultat ; en échec, la raison en clair.
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
