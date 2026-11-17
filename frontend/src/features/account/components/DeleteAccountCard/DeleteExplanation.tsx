import { t } from "@/shared/i18n/t";

/**
 * Ce que « Tout supprimer » efface, ce qu'il laisse, et où il mène ensuite. Un seul bloc nommé
 * (`id`) : le champ de confirmation le cite, et un lecteur d'écran entend l'avertissement en
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
