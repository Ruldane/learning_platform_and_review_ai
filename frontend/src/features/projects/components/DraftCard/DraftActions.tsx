import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export type CopyState = "idle" | "copied" | "failed";

interface DraftActionsProps {
  /** The text has changed since the last save. */
  canSave: boolean;
  saving: boolean;
  copy: CopyState;
  onSave: () => void;
  onCopy: () => void;
}

/** « Enregistrer » and « Copier » buttons, and the status region confirming the copy. */
export function DraftActions({ canSave, saving, copy, onSave, onCopy }: DraftActionsProps) {
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {/* `aria-disabled` not `disabled`: the button keeps focus during and after sending. */}
        <Button
          aria-disabled={saving || !canSave}
          onClick={() => {
            if (!saving && canSave) onSave();
          }}
        >
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
