import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

/**
 * The two choices on the screen. A component cannot import the generated contract (ESLint
 * boundaries): `types.test.ts` checks at compile time that this type is the contract's.
 */
export type Choice = "take_local" | "fresh";

interface ClaimChoiceProps {
  onChoose: (choice: Choice) => void;
  /** A send is in progress: the buttons keep focus but do nothing. */
  pending: boolean;
  error?: string | null;
}

/**
 * The very first sign-in choice: resume this computer's space or start
 * an empty one. While sending, the buttons switch to `aria-disabled` (not `disabled`): focus
 * of the keyboard user stays on the button they pressed.
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
