import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DeleteConfirm } from "./DeleteConfirm";

interface ItemActionsProps {
  busy: boolean;
  onEdit: () => void;
  onDelete: () => void;
}

/** Modifier et supprimer ; la suppression passe par une confirmation en ligne. */
export function ItemActions({ busy, onEdit, onDelete }: ItemActionsProps) {
  const [confirming, setConfirming] = useState(false);
  if (confirming) {
    return <DeleteConfirm busy={busy} onConfirm={onDelete} onKeep={() => setConfirming(false)} />;
  }
  return (
    <div className="flex gap-2">
      <Button variant="outline" disabled={busy} onClick={onEdit}>
        {t("memory.button.edit")}
      </Button>
      <Button variant="destructive" disabled={busy} onClick={() => setConfirming(true)}>
        {t("memory.button.delete")}
      </Button>
    </div>
  );
}
