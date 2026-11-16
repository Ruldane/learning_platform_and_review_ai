import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export type CopyState = "idle" | "copied" | "failed";

interface DraftActionsProps {
  /** Le texte a changé depuis le dernier enregistrement. */
  canSave: boolean;
  saving: boolean;
  copy: CopyState;
  onSave: () => void;
  onCopy: () => void;
}

/** « Enregistrer » et « Copier », et la région d'état qui confirme (ou rate) la copie. */
export function DraftActions({ canSave, saving, copy, onSave, onCopy }: DraftActionsProps) {
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button disabled={saving || !canSave} onClick={onSave}>
          {saving ? t("projects.draft.saving") : t("projects.draft.save")}
        </Button>
        <Button variant="outline" onClick={onCopy}>
          {t("projects.draft.copy")}
        </Button>
      </div>
      <p role="status" className="min-h-5 text-xs text-muted-foreground">
        {copy === "copied" && t("projects.draft.copied")}
        {copy === "failed" && t("projects.draft.copyFailed")}
      </p>
    </>
  );
}
