import { t } from "@/shared/i18n/t";
import type { ExchangeView, ExpectedView } from "../viewTypes";
import { NoteLine } from "./NoteLine";
import { Said } from "./Said";

interface ExchangeListProps {
  exchanges: ExchangeView[];
  /** Les questions de note 2 au plus (« à revoir »). */
  missed?: number[];
  /** Ce qu'une bonne réponse aurait donné, par question. */
  expected?: ExpectedView[];
  /** Montrer la note de chaque réponse (sans débrief, les notes ne disent rien). */
  showNotes?: boolean;
}

/** Les questions de l'entretien, la réponse de January, la relance éventuelle et, avec un débrief, la note de chacune. */
export function ExchangeList({
  exchanges,
  missed = [],
  expected = [],
  showNotes = true,
}: ExchangeListProps) {
  return (
    <div className="flex flex-col gap-3">
      {exchanges.map((exchange) => {
        const points = expected.find((entry) => entry.index === exchange.index)?.points ?? [];
        const review = showNotes && missed.includes(exchange.index);
        return (
          <article
            key={exchange.index}
            aria-label={t("applications.debrief.question", { number: exchange.index + 1 })}
            className="flex flex-col gap-2 rounded-lg border bg-card p-3"
          >
            <p className="font-medium">{exchange.question}</p>
            <dl className="flex flex-col gap-2">
              <Said label={t("applications.debrief.yourAnswer")} text={exchange.answer} />
              {exchange.followUp ? (
                <>
                  <Said label={t("applications.debrief.followUp")} text={exchange.followUp} />
                  <Said
                    label={t("applications.debrief.followUpAnswer")}
                    text={exchange.followUpAnswer}
                  />
                </>
              ) : null}
            </dl>
            {showNotes ? <NoteLine exchange={exchange} review={review} /> : null}
            {review && points.length > 0 ? (
              <div className="text-sm">
                <p className="text-muted-foreground">{t("applications.debrief.expected")}</p>
                <ul className="list-disc pl-5">
                  {points.map((point, index) => (
                    <li key={index}>{point}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
