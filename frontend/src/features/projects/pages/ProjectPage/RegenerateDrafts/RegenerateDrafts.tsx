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
 * le bouton disparaît, et le bouton le reprend quand le suivi disparaît (à la réussite, le titre
 * de la section des brouillons le reprend, voir `DraftsSection`).
 */
export function RegenerateDrafts({ regeneration, run }: RegenerateDraftsProps) {
  const started = regeneration.sessionId !== null;
  const ended = started && run.over;
  const writing = started && !run.over;
  const button = useFocusOnMount<HTMLButtonElement>(ended);
  // Tant que le projet se relit, les brouillons peuvent être sur le point d'arriver : rien à dire.
  const failed = ended && !regeneration.rereading;
  // La zone `status` existe dès le début, vide : un texte inséré avec sa zone n'est pas annoncé de
  // façon fiable. Elle reste la même pendant le suivi, puis quand le bouton revient.
  return (
    <div className="flex flex-col items-start gap-2">
      <p role="status" className="empty:sr-only">
        {failed ? t("projects.page.draftsFailed") : null}
      </p>
      {writing ? (
        <div className="self-stretch">
          <RunPanel
            title={t("projects.page.draftsWriting")}
            text={t("projects.page.draftsWritingText")}
            run={run}
            sessionId={regeneration.sessionId}
            focusOnMount
          />
        </div>
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}
