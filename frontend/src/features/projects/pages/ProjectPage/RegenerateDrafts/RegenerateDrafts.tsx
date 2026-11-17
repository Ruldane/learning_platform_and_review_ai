import { t } from "@/shared/i18n/t";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { DraftsRegeneration } from "../../../hooks/useRegenerateDrafts";
import type { useProjectRun } from "../../../hooks/useProjectRun";
import { RunPanel } from "../RunPanel";

interface RegenerateDraftsProps {
  regeneration: DraftsRegeneration;
  run: ReturnType<typeof useProjectRun>;
}

/**
 * Un projet validé sans aucun brouillon : « Régénérer les brouillons », puis le suivi de leur
 * écriture ; si elle se termine sans brouillon (échec, annulation, fin sans résultat), le bouton
 * revient avec la raison. Le focus ne tombe jamais sur `body` : le titre du suivi le prend quand
 * le bouton disparaît, et le bouton le reprend quand le suivi disparaît.
 */
export function RegenerateDrafts({ regeneration, run }: RegenerateDraftsProps) {
  const started = regeneration.sessionId !== null;
  const ended = started && run.over;
  const button = useFocusOnMount<HTMLButtonElement>(ended);
  if (started && !run.over) {
    return (
      <RunPanel
        title={t("projects.page.draftsWriting")}
        text={t("projects.page.draftsWritingText")}
        run={run}
        sessionId={regeneration.sessionId}
        focusOnMount
      />
    );
  }
  // Tant que le projet se relit, les brouillons peuvent être sur le point d'arriver : rien à dire.
  const failed = ended && !regeneration.rereading;
  return (
    <div className="flex flex-col items-start gap-2">
      {failed ? <p role="status">{t("projects.page.draftsFailed")}</p> : null}
      <Button
        ref={button}
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
