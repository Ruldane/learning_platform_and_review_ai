import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ProposalActionsProps {
  /** The code has changed since: accepting is no longer possible (and refusing has no purpose). */
  stale: boolean;
  /** A decision is in progress: the buttons ignore clicks but keep focus. */
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
}

/** « Accepter » and « Refuser »: the server applies or files it, the front rewrites nothing. */
export function ProposalActions({ stale, busy, onAccept, onReject }: ProposalActionsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button size="sm" disabled={stale} aria-disabled={busy} onClick={busy ? undefined : onAccept}>
        {t("ide.proposal.accept")}
      </Button>
      {stale ? null : (
        <Button
          size="sm"
          variant="outline"
          aria-disabled={busy}
          onClick={busy ? undefined : onReject}
        >
          {t("ide.proposal.reject")}
        </Button>
      )}
    </div>
  );
}
