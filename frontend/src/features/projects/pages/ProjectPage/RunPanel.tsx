import { t } from "@/shared/i18n/t";
import type { Run } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface RunPanelProps {
  title: string;
  text: string;
  /** Une phrase de plus, au-dessus du fil (par exemple « Une évaluation était déjà en cours »). */
  note?: string | null;
  run: Run;
  /** La session du projet ; `null` tant que la lecture ne la donne pas. */
  sessionId: string | null;
}

/**
 * Ce que le Praticien fait pour le projet (écrire l'énoncé, évaluer le rendu), suivi en direct : le
 * fil dit où il en est, le résultat vient toujours de la relecture du projet.
 */
export function RunPanel({ title, text, note = null, run, sessionId }: RunPanelProps) {
  return (
    <section aria-label={title} className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">{title}</h2>
      <p className="text-sm text-muted-foreground">{text}</p>
      {note ? (
        <p role="status" className="text-sm text-muted-foreground">
          {note}
        </p>
      ) : null}
      {sessionId ? (
        <RunFeed run={run} label={t("projects.page.feed")} />
      ) : (
        <LoadingState label={t("projects.page.waitingSession")} />
      )}
    </section>
  );
}
