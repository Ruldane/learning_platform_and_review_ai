import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useDeletePosting } from "../../hooks/useDeletePosting";

interface DeleteSectionProps {
  postingId: string;
  onDeleted: () => void;
}

/** « Supprimer » avec une confirmation dans la page (jamais `window.confirm`) ; Échap annule. */
export function DeleteSection({ postingId, onDeleted }: DeleteSectionProps) {
  const [asking, setAsking] = useState(false);
  const { remove, pending, error, reset } = useDeletePosting(postingId, onDeleted);
  const cancel = () => {
    reset();
    setAsking(false);
  };

  if (!asking) {
    return (
      <Button variant="outline" className="self-start" onClick={() => setAsking(true)}>
        {t("gap.posting.delete")}
      </Button>
    );
  }
  return (
    <div
      role="group"
      aria-label={t("gap.posting.deleteAsk")}
      onKeyDown={(event) => {
        if (event.key === "Escape" && !pending) cancel();
      }}
      className="flex flex-col items-start gap-2 rounded-xl border border-destructive/40 bg-card p-3"
    >
      <p className="font-medium">{t("gap.posting.deleteAsk")}</p>
      <p className="text-sm text-muted-foreground">{t("gap.posting.deleteHint")}</p>
      {error ? <InlineError message={error} /> : null}
      <div className="flex gap-2">
        <Button variant="destructive" onClick={remove} disabled={pending}>
          {pending ? t("gap.posting.deleting") : t("gap.posting.deleteConfirm")}
        </Button>
        <Button variant="outline" onClick={cancel} disabled={pending} autoFocus>
          {t("gap.posting.deleteCancel")}
        </Button>
      </div>
    </div>
  );
}
