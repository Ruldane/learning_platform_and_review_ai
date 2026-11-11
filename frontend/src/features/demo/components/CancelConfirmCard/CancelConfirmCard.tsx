import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface CancelConfirmCardProps {
  disabled: boolean;
  onConfirm: () => void;
  onKeep: () => void;
}

/** Confirmation d'annulation dans la page (jamais `window.confirm`). */
export function CancelConfirmCard({ disabled, onConfirm, onKeep }: CancelConfirmCardProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="rounded-xl border-2 border-destructive/60 bg-card px-4 py-3"
    >
      <p id={titleId} className="font-medium">
        {t("demo.cancel.title")}
      </p>
      <p className="text-sm text-muted-foreground">{t("demo.cancel.description")}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button variant="destructive" disabled={disabled} onClick={onConfirm}>
          {t("demo.cancel.confirm")}
        </Button>
        <Button variant="outline" autoFocus onClick={onKeep}>
          {t("demo.cancel.keep")}
        </Button>
      </div>
    </section>
  );
}
