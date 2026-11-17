import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { DraftsRegeneration } from "../../hooks/useRegenerateDrafts";
import type { useProjectRun } from "../../hooks/useProjectRun";
import { RunPanel } from "./RunPanel";

interface RegenerateDraftsProps {
  regeneration: DraftsRegeneration;
  run: ReturnType<typeof useProjectRun>;
}

/**
 * Un projet validé sans aucun brouillon : « Régénérer les brouillons », puis le suivi de leur
 * écriture ; si elle échoue, le bouton revient avec la raison.
 */
export function RegenerateDrafts({ regeneration, run }: RegenerateDraftsProps) {
  const started = regeneration.sessionId !== null;
  if (started && !run.over) {
    return (
      <RunPanel
        title={t("projects.page.draftsWriting")}
        text={t("projects.page.draftsWritingText")}
        run={run}
        sessionId={regeneration.sessionId}
      />
    );
  }
  return (
    <div className="flex flex-col items-start gap-2">
      {started && run.stream.status === "failed" ? (
        <p role="status">{t("projects.page.draftsFailed")}</p>
      ) : null}
      <Button
        aria-disabled={regeneration.pending}
        onClick={() => !regeneration.pending && regeneration.regenerate()}
      >
        {regeneration.pending
          ? t("projects.page.draftsRegenerating")
          : t("projects.page.draftsRegenerate")}
      </Button>
      {regeneration.error ? <InlineError message={regeneration.error} /> : null}
    </div>
  );
}
