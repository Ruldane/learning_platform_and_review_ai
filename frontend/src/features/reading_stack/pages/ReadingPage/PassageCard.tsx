import { useId } from "react";
import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { makeReadingCard } from "../../api";

const MAX_PASSAGE = 1200;

export function PassageCard({ id, passage }: { id: string; passage: string }) {
  const card = useMutation({ mutationFn: (text: string) => makeReadingCard(id, text) });
  const notice = useId();
  const tooLong = Array.from(passage).length > MAX_PASSAGE;
  return (
    <>
      <Button
        variant="outline"
        className="self-start"
        disabled={!passage || tooLong || card.isPending}
        aria-describedby={tooLong ? notice : undefined}
        onPointerDown={(event) => event.preventDefault()}
        onClick={() => card.mutate(passage)}
      >
        {t("reading.glossary.makeCard")}
      </Button>
      {tooLong ? (
        <p id={notice} role="status" className="text-sm">
          {t("reading.glossary.passageTooLong", { limit: MAX_PASSAGE.toLocaleString("en-GB") })}
        </p>
      ) : null}
      {card.data ? (
        <p role="status" className="text-sm">
          {t(card.data.count ? "reading.actions.cardDone" : "reading.actions.cardExisting")}
        </p>
      ) : null}
      {card.error ? <InlineError message={errorMessage(card.error)} /> : null}
    </>
  );
}
