import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

export type Choice = "take_local" | "fresh";

interface ClaimChoiceProps {
  onChoose: (choice: Choice) => void;
  /** Un envoi est en cours : les boutons restent au focus mais ne font plus rien. */
  pending: boolean;
  error?: string | null;
}

/**
 * Le choix de la toute première connexion : reprendre l'espace de cet ordinateur ou en commencer
 * un vide. Pendant l'envoi les boutons passent en `aria-disabled` (et non `disabled`) : le focus
 * de la personne au clavier reste sur le bouton qu'elle a pressé.
 */
export function ClaimChoice({ onChoose, pending, error }: ClaimChoiceProps) {
  const choose = (choice: Choice) => () => {
    if (!pending) onChoose(choice);
  };
  return (
    <section className="flex flex-col gap-5 rounded-xl border border-border bg-card px-6 py-8">
      <p className="text-muted-foreground">{t("auth.claim.intro")}</p>
      <div className="flex flex-col gap-1">
        <Button aria-disabled={pending} onClick={choose("take_local")} className="self-start">
          {t("auth.claim.take")}
        </Button>
        <p className="text-sm text-muted-foreground">{t("auth.claim.takeHint")}</p>
      </div>
      <div className="flex flex-col gap-1">
        <Button
          variant="outline"
          aria-disabled={pending}
          onClick={choose("fresh")}
          className="self-start"
        >
          {t("auth.claim.fresh")}
        </Button>
        <p className="text-sm text-muted-foreground">{t("auth.claim.freshHint")}</p>
      </div>
      <p role="status" className="text-sm text-muted-foreground">
        {pending ? t("auth.claim.pending") : null}
      </p>
      {error ? <InlineError message={error} /> : null}
    </section>
  );
}
