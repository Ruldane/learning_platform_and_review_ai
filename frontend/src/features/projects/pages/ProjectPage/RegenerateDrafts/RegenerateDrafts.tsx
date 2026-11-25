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
 * A validated project with no drafts: « Régénérer les brouillons », then the tracker of their
 * write; if it ends without drafts (failure, cancel, end with no result), the button
 * returns with the reason. Focus never falls on `body`: the tracker's title takes it when
 * the button disappears, and the button takes it back when the tracker disappears (on success,
 * the drafts section title takes it back, see `DraftsSection`).
 */
export function RegenerateDrafts({ regeneration, run }: RegenerateDraftsProps) {
  const started = regeneration.sessionId !== null;
  const ended = started && run.over;
  const writing = started && !run.over;
  const button = useFocusOnMount<HTMLButtonElement>(ended);
  // While the project re-reads, drafts may be about to arrive: nothing to say.
  const failed = ended && !regeneration.rereading;
  // The `status` region exists from the start, empty: text inserted with its region is not reliably
  // announced. It stays the same during the tracking, and when the button returns.
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
