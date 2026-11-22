import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { makeReadingCard } from "../../api";

export function PassageCard({ id, passage }: { id: string; passage: string }) {
  const card = useMutation({ mutationFn: (text: string) => makeReadingCard(id, text) });
  return (
    <>
      <Button
        variant="outline"
        className="self-start"
        disabled={!passage || card.isPending}
        onPointerDown={(event) => event.preventDefault()}
        onClick={() => card.mutate(passage)}
      >
        {t("reading.glossary.makeCard")}
      </Button>
      {card.data ? (
        <p role="status" className="text-sm">
          {t(card.data.count ? "reading.actions.cardDone" : "reading.actions.cardExisting")}
        </p>
      ) : null}
      {card.error ? <InlineError message={errorMessage(card.error)} /> : null}
    </>
  );
}
