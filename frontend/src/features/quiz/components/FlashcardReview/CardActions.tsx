import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

/** The key badge, decorative: `aria-keyshortcuts` already tells screen readers. */
const KEY_CLASS = "ml-1.5 rounded border border-current/30 px-1 font-sans text-xs";

interface CardActionsProps {
  flipped: boolean;
  busy: boolean;
  onReveal: () => void;
  onResult: (result: "ok" | "fail") => void;
}

/** « Voir la réponse » (Space) before the back, « Raté » (1) and « Su » (2) after. */
export function CardActions({ flipped, busy, onReveal, onResult }: CardActionsProps) {
  if (!flipped) {
    return (
      <Button disabled={busy} aria-keyshortcuts="Space" onClick={onReveal}>
        {t("quiz.card.reveal")}
        <kbd aria-hidden="true" className={KEY_CLASS}>
          Espace
        </kbd>
      </Button>
    );
  }
  return (
    <>
      <Button
        variant="outline"
        disabled={busy}
        aria-keyshortcuts="1"
        onClick={() => onResult("fail")}
      >
        {t("quiz.card.fail")}
        <kbd aria-hidden="true" className={KEY_CLASS}>
          1
        </kbd>
      </Button>
      <Button disabled={busy} aria-keyshortcuts="2" onClick={() => onResult("ok")}>
        {t("quiz.card.ok")}
        <kbd aria-hidden="true" className={KEY_CLASS}>
          2
        </kbd>
      </Button>
    </>
  );
}
