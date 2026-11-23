import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { Destination } from "../../navigation";
import { NavItemLabel } from "../../layout/NavItemLabel";

export function DestinationCards({
  cards,
  tools,
}: {
  cards: Destination[];
  tools?: (card: Destination) => ReactNode;
}) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2">
      {cards.map((card) => {
        const name = t(card.labelKey);
        return (
          <li key={card.path} data-feature={card.id} className="flex flex-col gap-3 rounded-xl border bg-card p-5 shadow-sm">
            <h2 className="text-base font-semibold"><NavItemLabel item={card} /></h2>
            <p className="flex-1 text-sm text-muted-foreground">{t(card.description)}</p>
            {tools?.(card)}
            <Link
              to={card.path}
              aria-label={t("navigation.open", { name })}
              className="flex w-fit items-center gap-2 rounded-sm text-sm font-semibold text-primary underline-offset-4 hover:underline"
            >
              {t("navigation.open", { name })}
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
