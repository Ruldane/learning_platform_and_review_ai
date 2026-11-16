import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface EntryFooterProps {
  added: boolean;
  /** La version du profil maître qui a reçu l'entrée, quand on la connaît. */
  version?: number | null;
  busy: boolean;
}

/**
 * Le pied du formulaire : le rappel de consentement, puis le bouton d'ajout, que l'état « Ajouté au
 * profil (version N) » remplace une fois l'entrée dans le profil. La région d'état est toujours là :
 * le changement est annoncé.
 */
export function EntryFooter({ added, version = null, busy }: EntryFooterProps) {
  return (
    <>
      <p className="text-sm text-muted-foreground">{t("projects.entry.notice")}</p>
      <p role="status" className="text-sm font-medium">
        {added
          ? version === null
            ? t("projects.entry.added")
            : t("projects.entry.addedVersion", { version })
          : null}
      </p>
      {added ? null : (
        <Button type="submit" className="self-start" disabled={busy}>
          {busy ? t("projects.entry.adding") : t("projects.entry.add")}
        </Button>
      )}
    </>
  );
}
