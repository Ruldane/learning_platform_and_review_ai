import { t } from "@/shared/i18n/t";

/**
 * What « Tout supprimer » erases, what it keeps, and where it leads next. A single block named
 * (`id`): the confirmation field cites it, and a screen reader announces the warning as
 * arrivant dessus.
 */
export function DeleteExplanation({ id }: { id: string }) {
  return (
    <div id={id} className="flex flex-col gap-3">
      <p className="text-sm font-medium text-destructive">{t("account.delete.warning")}</p>
      <p className="text-sm text-muted-foreground">{t("account.delete.scope")}</p>
      <p className="text-sm text-muted-foreground">{t("account.delete.keep")}</p>
      <p className="text-sm text-muted-foreground">{t("account.delete.after")}</p>
    </div>
  );
}
