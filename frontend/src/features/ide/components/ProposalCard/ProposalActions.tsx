import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ProposalActionsProps {
  /** Le code a changé depuis : accepter n'est plus possible (et refuser n'a plus d'objet). */
  stale: boolean;
  /** Une décision est en cours : les boutons ignorent les clics mais gardent le focus. */
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
}

/** « Accepter » et « Refuser » : le serveur applique ou classe, le front ne réécrit rien. */
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
