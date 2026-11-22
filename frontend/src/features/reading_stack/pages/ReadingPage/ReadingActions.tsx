import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { keepReading, makeReadingCard, type ReadingDetail } from "../../api";
import { ReadingApplication } from "./ReadingApplication";
import { ReadingPlan } from "./ReadingPlan";

export function ReadingActions({ article }: { article: ReadingDetail }) {
  const memory = useMutation({ mutationFn: () => keepReading(article.id) });
  const card = useMutation({ mutationFn: () => makeReadingCard(article.id) });
  const error = memory.error ?? card.error;
  return (
    <section aria-label={t("reading.actions.label")} className="flex flex-col gap-3 border-t pt-3">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" disabled={memory.isPending} onClick={() => memory.mutate()}>
          {t("reading.actions.memory")}
        </Button>
        {article.summary || article.text ? (
          <Button variant="outline" disabled={card.isPending} onClick={() => card.mutate()}>
            {t("reading.actions.card")}
          </Button>
        ) : null}
      </div>
      {memory.data ? (
        <Link
          className="self-start text-sm underline"
          to={`/memoire?item=${memory.data.memory_item_id}`}
        >
          {t("reading.actions.openMemory")}
        </Link>
      ) : null}
      {card.data ? (
        <p role="status" className="text-sm">
          {t(card.data.count ? "reading.actions.cardDone" : "reading.actions.cardExisting")}
        </p>
      ) : null}
      {error ? <InlineError message={errorMessage(error)} /> : null}
      <ReadingPlan id={article.id} />
      {article.kind === "offer" ? (
        <ReadingApplication id={article.id} company={article.company} />
      ) : null}
    </section>
  );
}
