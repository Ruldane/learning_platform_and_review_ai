import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

interface CardsSectionProps {
  count: number;
  reviewsHref: string;
}

/** The review cards created by the interview, with the link to the reviews page. */
export function CardsSection({ count, reviewsHref }: CardsSectionProps) {
  const message =
    count === 0
      ? t("applications.debrief.cards.none")
      : t(`applications.debrief.cards.${count === 1 ? "one" : "many"}`, { count });
  return (
    <section className="flex flex-col items-start gap-2">
      <h3 className="text-lg font-semibold">{t("applications.debrief.cards.title")}</h3>
      <p>{message}</p>
      {count > 0 ? (
        <Link
          to={reviewsHref}
          className="text-sm font-medium text-primary underline underline-offset-4"
        >
          {t("applications.debrief.cards.open")}
        </Link>
      ) : null}
    </section>
  );
}
