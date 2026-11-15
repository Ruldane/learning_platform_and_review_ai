import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface KitPieceFooterProps {
  title: string;
  /** La pièce a un texte à enregistrer (elle n'est pas « pas encore arrivée »). */
  editable: boolean;
  dirty: boolean;
  saving: boolean;
  /** Le dernier résultat (copié, enregistré…), lu dans une zone vocale. */
  note: string;
  /** Le refus du serveur. */
  error: string;
  onSave: () => void;
}

/** Le bouton Enregistrer (explicite), le refus éventuel et la zone vocale du dernier résultat. */
export function KitPieceFooter({
  title,
  editable,
  dirty,
  saving,
  note,
  error,
  onSave,
}: KitPieceFooterProps) {
  return (
    <>
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
            disabled={!dirty || saving}
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
