import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface EntryFooterProps {
  added: boolean;
  busy: boolean;
  /** Le formulaire est verrouillé : entrée déjà ajoutée, ou ajout en cours. */
  locked: boolean;
}

/** Le pied du formulaire : le rappel de consentement, l'état « ajouté » et le bouton d'ajout. */
export function EntryFooter({ added, busy, locked }: EntryFooterProps) {
  return (
    <>
      <p className="text-sm text-muted-foreground">{t("projects.entry.notice")}</p>
      {added ? (
        <p role="status" className="text-sm font-medium">
          {t("projects.entry.added")}
        </p>
      ) : null}
      <Button type="submit" className="self-start" disabled={locked}>
        {busy ? t("projects.entry.adding") : t("projects.entry.add")}
      </Button>
    </>
  );
}
