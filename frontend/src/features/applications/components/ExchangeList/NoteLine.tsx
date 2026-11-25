import { t } from "@/shared/i18n/t";
import type { ExchangeView } from "../viewTypes";

interface NoteLineProps {
  exchange: ExchangeView;
  /** The question needs review (score of 2 at most). */
  review: boolean;
}

/** An answer's score in words (« 2 sur 5 » or « Non notée »), and « À revoir » if needed. */
export function NoteLine({ exchange, review }: NoteLineProps) {
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm">
      <span className="font-medium">
        {exchange.unrated
          ? t("applications.debrief.unratedNote")
          : t("applications.debrief.note", { value: exchange.note })}
      </span>
      {review ? (
        <span className="rounded-md border px-2 py-0.5 text-xs font-medium">
          {t("applications.debrief.toReview")}
        </span>
      ) : null}
    </p>
  );
}
