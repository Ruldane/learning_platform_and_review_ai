import { Zap } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { useCaptureDialog } from "./captureDialog";

/** Le bouton de la barre du haut qui ouvre la capture rapide (le raccourci Ctrl+K fait de même). */
export function CaptureTopbarButton() {
  const openDialog = useCaptureDialog((state) => state.openDialog);
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={openDialog}
      aria-haspopup="dialog"
      aria-keyshortcuts="Control+K Meta+K"
    >
      <Zap aria-hidden="true" />
      {t("capture.topbar.button")}
      <kbd className="ml-1 rounded border border-border px-1 text-[0.7rem] text-muted-foreground">
        {t("capture.topbar.hint")}
      </kbd>
    </Button>
  );
}
