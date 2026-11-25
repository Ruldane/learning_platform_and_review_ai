import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { MAX_CONTENT } from "./parts";

interface KitPieceFooterProps {
  title: string;
  /** The piece has a text to save (it is not « pas encore arrivée »). */
  editable: boolean;
  dirty: boolean;
  /** The text exceeds what the server accepts. */
  tooLong: boolean;
  saving: boolean;
  /** The last result (copied, saved…), read in a live region. */
  note: string;
  /** The server's refusal. */
  error: string;
  onSave: () => void;
}

/** The Save button (explicit), the possible refusal and the live region for the last result. */
export function KitPieceFooter({
  title,
  editable,
  dirty,
  tooLong,
  saving,
  note,
  error,
  onSave,
}: KitPieceFooterProps) {
  return (
    <>
      {tooLong ? (
        <p role="alert" className="text-sm text-destructive">
          {t("applications.kitPiece.tooLong", { max: MAX_CONTENT.toLocaleString("en-GB") })}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        {editable ? (
          <Button
            type="button"
            size="sm"
            disabled={!dirty || tooLong || saving}
            aria-label={t("applications.kitPiece.saveOf", { name: title })}
            onClick={onSave}
          >
            {saving ? t("applications.kitPiece.saving") : t("applications.kitPiece.save")}
          </Button>
        ) : null}
        <p role="status" className="min-h-5 text-xs text-muted-foreground">
          {dirty && !note ? t("applications.kitPiece.unsaved") : note}
        </p>
      </div>
    </>
  );
}
