import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface MergeConfirmProps {
  count: number;
  targetTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Confirmation de fusion en ligne (jamais `window.confirm`) : la fusion supprime les autres éléments. */
export function MergeConfirm({ count, targetTitle, onConfirm, onCancel }: MergeConfirmProps) {
  const questionId = useId();
  return (
    <div
      role="group"
      aria-labelledby={questionId}
      className="flex flex-wrap items-center gap-3 rounded-xl border-2 border-destructive/60 px-4 py-3"
    >
      <p id={questionId} className="font-medium">
        {t("memory.table.mergeAsk", { count, title: targetTitle })}
      </p>
      <Button variant="destructive" onClick={onConfirm}>
        {t("memory.table.mergeYes")}
      </Button>
      <Button variant="outline" autoFocus onClick={onCancel}>
        {t("memory.table.mergeNo")}
      </Button>
    </div>
  );
}
