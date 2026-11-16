import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface EntryFooterProps {
  added: boolean;
  /** La version du profil maître qui a reçu l'entrée, quand on la connaît. */
  version?: number | null;
  busy: boolean;
  /** Le clic sur le bouton : le seul geste qui ajoute l'entrée (Entrée dans un champ n'envoie rien). */
  onAdd: () => void;
}

/**
 * Le pied du formulaire : le rappel de consentement, puis le bouton d'ajout, que l'état « Ajouté au
 * profil (version N) » remplace une fois l'entrée dans le profil. La région d'état est toujours là :
 * le changement est annoncé, et elle reprend le focus du bouton qui disparaît.
 */
export function EntryFooter({ added, version = null, busy, onAdd }: EntryFooterProps) {
  const status = useRef<HTMLParagraphElement>(null);
  const wasAdded = useRef(added);
  useEffect(() => {
    // Le bouton cliqué vient d'être remplacé : le focus serait tombé sur `body`.
    if (added && !wasAdded.current && document.activeElement === document.body) {
      status.current?.focus();
    }
    wasAdded.current = added;
  }, [added]);
  return (
    <>
      <p className="text-sm text-muted-foreground">{t("projects.entry.notice")}</p>
      <p ref={status} tabIndex={-1} role="status" className="text-sm font-medium outline-none">
        {added
          ? version === null
            ? t("projects.entry.added")
            : t("projects.entry.addedVersion", { version })
          : null}
      </p>
      {added ? null : (
        <Button
          type="button"
          className="self-start"
          aria-disabled={busy}
          onClick={() => !busy && onAdd()}
        >
          {busy ? t("projects.entry.adding") : t("projects.entry.add")}
        </Button>
      )}
    </>
  );
}
