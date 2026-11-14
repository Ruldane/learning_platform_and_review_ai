import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ModificationStatusView } from "../viewTypes";

interface DecisionButtonsProps {
  status: ModificationStatusView;
  /** Faux tant qu'un fait à confirmer n'est pas confirmé : « Accepter » reste désactivé. */
  confirmed: boolean;
  busy: boolean;
  onAccept: () => void;
  onRefuse: () => void;
  /** `null` pour un retrait ou un déplacement : il n'y a pas de texte à corriger. */
  onEdit: (() => void) | null;
}

/** Accepter, refuser, modifier : le bouton de l'état déjà pris est désactivé. */
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
