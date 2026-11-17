import { Button } from "@/shared/ui/button";

interface SaveBarProps {
  pending: boolean;
  saved: boolean;
  dirty: boolean;
  /** Rien à enregistrer, saisie invalide ou envoi en cours. */
  blocked: boolean;
  labels: { save: string; saving: string; saved: string; unsaved: string };
}

/**
 * Le bouton « Enregistrer » d'un formulaire et la phrase d'état (enregistré, non enregistré) annoncée. Bloqué par `aria-disabled` (jamais `disabled`) :
 * le focus reste sur le bouton une fois l'enregistrement fini ; le formulaire ignore l'envoi bloqué.
 */
export function SaveBar({ pending, saved, dirty, blocked, labels }: SaveBarProps) {
  return (
    <div className="flex items-center gap-3">
      <Button type="submit" aria-disabled={blocked}>
        {pending ? labels.saving : labels.save}
      </Button>
      <p role="status" className="text-sm text-muted-foreground">
        {saved && !dirty ? labels.saved : null}
        {dirty && !pending ? labels.unsaved : null}
      </p>
    </div>
  );
}
