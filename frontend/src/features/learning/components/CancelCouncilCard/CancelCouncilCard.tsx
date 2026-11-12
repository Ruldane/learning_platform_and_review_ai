import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface CancelCouncilCardProps {
  disabled: boolean;
  onConfirm: () => void;
  onKeep: () => void;
}

/** Confirmation d'arrêt du Conseil dans la page (jamais `window.confirm`). */
export function CancelCouncilCard({ disabled, onConfirm, onKeep }: CancelCouncilCardProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="rounded-xl border-2 border-destructive/60 bg-card px-4 py-3"
    >
      <p id={titleId} className="font-medium">
        {t("learning.council.cancelTitle")}
      </p>
      <p className="text-sm text-muted-foreground">{t("learning.council.cancelHelp")}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button variant="destructive" disabled={disabled} onClick={onConfirm}>
          {t("learning.council.cancelConfirm")}
        </Button>
        <Button variant="outline" autoFocus onClick={onKeep}>
          {t("learning.council.cancelKeep")}
        </Button>
      </div>
    </section>
  );
}
