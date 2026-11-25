import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface TakeTheirsProps {
  file: string;
  onConfirm: () => void;
}

/** « Prendre celle de Claude »: discards your edits, so it asks for confirmation first. */
export function TakeTheirs({ file, onConfirm }: TakeTheirsProps) {
  const [confirming, setConfirming] = useState(false);
  if (!confirming) {
    return (
      <Button variant="outline" className="w-fit" onClick={() => setConfirming(true)}>
        {t("ide.claude.takeTheirs")}
      </Button>
    );
  }
  return (
    <div role="group" aria-label={t("ide.claude.takeTheirs")} className="flex flex-col gap-2">
      <p className="text-sm font-medium">{t("ide.claude.discardWarning", { file })}</p>
      <div className="flex flex-wrap gap-2">
        <Button variant="destructive" onClick={onConfirm}>
          {t("ide.claude.discardMine")}
        </Button>
        <Button variant="outline" onClick={() => setConfirming(false)}>
          {t("ide.claude.cancel")}
        </Button>
      </div>
    </div>
  );
}
