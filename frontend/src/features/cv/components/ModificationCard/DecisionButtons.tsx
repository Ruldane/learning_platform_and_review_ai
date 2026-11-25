import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ModificationStatusView } from "../viewTypes";

interface DecisionButtonsProps {
  status: ModificationStatusView;
  /** False until a fact to confirm is confirmed: « Accepter » stays disabled. */
  confirmed: boolean;
  busy: boolean;
  onAccept: () => void;
  onRefuse: () => void;
  /** `null` for a removal or a move: there is no text to correct. */
  onEdit: (() => void) | null;
}

/** Accept, refuse, edit: the button of the state already taken is disabled. */
export function DecisionButtons({
  status,
  confirmed,
  busy,
  onAccept,
  onRefuse,
  onEdit,
}: DecisionButtonsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button onClick={onAccept} disabled={busy || status === "accepted" || !confirmed}>
        {t("cv.mod.accept")}
      </Button>
      <Button variant="outline" onClick={onRefuse} disabled={busy || status === "refused"}>
        {t("cv.mod.refuse")}
      </Button>
      {onEdit ? (
        <Button variant="ghost" onClick={onEdit} disabled={busy}>
          {t("cv.mod.edit")}
        </Button>
      ) : null}
    </div>
  );
}
