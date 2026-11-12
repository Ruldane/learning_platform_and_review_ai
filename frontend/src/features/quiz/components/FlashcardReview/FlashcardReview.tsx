import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { CardView } from "../viewTypes";
import { CardActions } from "./CardActions";
import { useCardShortcuts } from "./useCardShortcuts";

interface FlashcardReviewProps {
  card: CardView;
  onResult: (result: "ok" | "fail") => void;
  /** Un avis est en route : boutons et raccourcis sont coupés. */
  busy: boolean;
}

/**
 * Une fiche de révision : le recto, « Voir la réponse » (Espace), puis « Raté » (1) ou « Su » (2).
 * Chaque nouvelle fiche repart du recto ; une fois le verso montré, le focus y va pour que la
 * réponse soit lue.
 */
export function FlashcardReview({ card, onResult, busy }: FlashcardReviewProps) {
  const [revealedId, setRevealedId] = useState<string | null>(null);
  const flipped = revealedId === card.id;
  const backRef = useRef<HTMLDivElement>(null);
  const reveal = () => setRevealedId(card.id);

  useEffect(() => {
    if (flipped) backRef.current?.focus();
  }, [flipped]);
  useCardShortcuts({ busy, flipped, onReveal: reveal, onResult });

  return (
    <section
      aria-label={t("quiz.card.label")}
      className="flex flex-col gap-4 rounded-xl border bg-card p-6"
    >
      {card.skill ? (
        <p className="text-xs text-muted-foreground">
          {t("quiz.card.skill", { skill: card.skill })}
        </p>
      ) : null}
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t("quiz.card.front")}
        </p>
        <p className="mt-1 whitespace-pre-wrap text-lg font-medium">{card.front}</p>
      </div>
      {flipped ? (
        <div
          ref={backRef}
          role="group"
          tabIndex={-1}
          aria-label={t("quiz.card.back")}
          className="rounded-lg bg-muted p-3 outline-none focus-visible:ring-3 focus-visible:ring-ring"
        >
          <p className="whitespace-pre-wrap">{card.back}</p>
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <CardActions flipped={flipped} busy={busy} onReveal={reveal} onResult={onResult} />
      </div>
      <p className="text-xs text-muted-foreground">{t("quiz.card.shortcuts")}</p>
    </section>
  );
}
