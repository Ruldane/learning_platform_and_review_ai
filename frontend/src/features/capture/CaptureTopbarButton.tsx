import { Zap } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { useCaptureDialog } from "./captureDialog";

/** The top bar button that opens quick capture (the Ctrl+K shortcut does the same). */
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
