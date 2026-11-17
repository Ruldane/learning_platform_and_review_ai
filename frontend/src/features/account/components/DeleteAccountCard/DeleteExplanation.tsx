import { t } from "@/shared/i18n/t";

/** Ce que « Tout supprimer » efface, ce qu'il laisse, et où il mène ensuite. */
export function DeleteExplanation() {
  return (
    <>
      <p className="text-sm font-medium text-destructive">{t("account.delete.warning")}</p>
      <p className="text-sm text-muted-foreground">{t("account.delete.scope")}</p>
      <p className="text-sm text-muted-foreground">{t("account.delete.keep")}</p>
      <p className="text-sm text-muted-foreground">{t("account.delete.after")}</p>
    </>
  );
}
