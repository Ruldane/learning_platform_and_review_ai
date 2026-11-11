import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface DeleteConfirmProps {
  busy: boolean;
  onConfirm: () => void;
  onKeep: () => void;
}

/** Confirmation de suppression dans le tiroir (jamais `window.confirm`). */
export function DeleteConfirm({ busy, onConfirm, onKeep }: DeleteConfirmProps) {
  const questionId = useId();
  return (
    <div
      role="group"
      aria-labelledby={questionId}
      className="flex flex-col gap-2 rounded-xl border-2 border-destructive/60 px-4 py-3"
    >
      <p id={questionId} className="font-medium">
        {t("memory.drawer.deleteAsk")}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="destructive" disabled={busy} onClick={onConfirm}>
          {t("memory.drawer.deleteYes")}
        </Button>
        <Button variant="outline" autoFocus onClick={onKeep}>
          {t("memory.drawer.deleteNo")}
        </Button>
      </div>
    </div>
  );
}
