import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface SaveBarProps {
  pending: boolean;
  saved: boolean;
  dirty: boolean;
  /** Rien à enregistrer, saisie invalide ou envoi en cours. */
  blocked: boolean;
  /** Un champ est hors bornes : la raison du blocage à dire, plutôt que « rien à enregistrer ». */
  invalid?: boolean;
  labels: { save: string; saving: string; saved: string; unsaved: string };
}

/**
 * Le bouton « Enregistrer » d'un formulaire et la phrase d'état (enregistré, non enregistré)
 * annoncée. Bloqué par `aria-disabled` (jamais `disabled`) : le focus reste sur le bouton une fois
 * l'enregistrement fini ; le formulaire ignore l'envoi bloqué. La raison du blocage est un texte
 * relié au bouton (`aria-describedby`), lu avec lui, jamais seulement une couleur.
 */
export function SaveBar({ pending, saved, dirty, blocked, invalid = false, labels }: SaveBarProps) {
  const reasonId = useId();
  const reason =
    blocked && !pending
      ? t(invalid ? "settings.fields.saveInvalid" : "settings.fields.saveClean")
      : null;
  return (
    <div className="flex items-center gap-3">
      <Button
        type="submit"
        aria-disabled={blocked}
        aria-describedby={reason ? reasonId : undefined}
      >
        {pending ? labels.saving : labels.save}
      </Button>
      {reason ? (
        <span id={reasonId} className="sr-only">
          {reason}
        </span>
      ) : null}
      <p role="status" className="text-sm text-muted-foreground">
        {saved && !dirty ? labels.saved : null}
        {dirty && !pending ? labels.unsaved : null}
      </p>
    </div>
  );
}
