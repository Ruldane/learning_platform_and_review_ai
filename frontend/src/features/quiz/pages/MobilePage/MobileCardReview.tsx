import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Answer, MobileCard } from "../../mobile/data";

export function MobileCardReview({ card, busy, answer }: {
  card: MobileCard;
  busy: boolean;
  answer: (result: Answer) => void;
}) {
  const [turn, setTurn] = useState(false);
  return (
    <article className="grid gap-3 rounded-lg border p-4">
      <p className="whitespace-pre-wrap break-words font-semibold">{card.front}</p>
      <Button variant="outline" className="justify-self-start"
        aria-expanded={turn} onClick={() => setTurn((current) => !current)}>
        {t(turn ? "mobile.hide" : "mobile.show")}
      </Button>
      {turn ? (
        <>
          <p className="whitespace-pre-wrap break-words">{card.back}</p>
          <div className="flex flex-wrap gap-2">
            <Button aria-disabled={busy} onClick={() => !busy && answer("ok")}>{t("mobile.correct")}</Button>
            <Button variant="outline" aria-disabled={busy}
              onClick={() => !busy && answer("fail")}>{t("mobile.retry")}</Button>
          </div>
        </>
      ) : null}
    </article>
  );
}
