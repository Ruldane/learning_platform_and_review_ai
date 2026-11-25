import { t } from "@/shared/i18n/t";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";
import type { Run } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface RunPanelProps {
  title: string;
  text: string;
  /** One more sentence, above the thread (for example « Une évaluation était déjà en cours »). */
  note?: string | null;
  run: Run;
  /** The project's session; `null` until the read provides it. */
  sessionId: string | null;
  /** The form or button that had focus has just disappeared: the title takes it back. */
  focusOnMount?: boolean;
}

/**
 * What the Practitioner does for the project (write the brief, evaluate the submission), live:
 * thread says where it is; the result always comes from re-reading the project.
 */
export function RunPanel(props: RunPanelProps) {
  const { title, text, note = null, run, sessionId, focusOnMount = false } = props;
  const heading = useFocusOnMount<HTMLHeadingElement>(focusOnMount);
  return (
    <section aria-label={title} className="flex flex-col gap-3">
      <h2 ref={heading} tabIndex={-1} className="text-lg font-medium outline-none">
        {title}
      </h2>
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
