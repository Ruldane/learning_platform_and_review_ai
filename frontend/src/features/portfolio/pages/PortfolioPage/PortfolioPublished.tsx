import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { Publication } from "../../api";
import { PortfolioLinks } from "./PortfolioLinks";
import { PortfolioWithdraw } from "./PortfolioWithdraw";

interface Props {
  value: Publication;
  reload: () => void;
  restoreFocus: () => void;
}

export function PortfolioPublished({ value, reload, restoreFocus }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">
        {t("portfolio.published")}
      </h2>
      {value.available ? (
        <>
          <a
            href={value.url}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all underline underline-offset-4"
          >
            {value.url}
          </a>
          <PortfolioLinks value={value} reload={reload} />
        </>
      ) : (
        <p>{t("portfolio.changedHost")}</p>
      )}
      <PortfolioWithdraw value={value} reload={reload} restoreFocus={restoreFocus} />
    </section>
  );
}
