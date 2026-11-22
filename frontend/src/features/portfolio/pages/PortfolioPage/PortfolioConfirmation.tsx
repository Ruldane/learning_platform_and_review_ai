import { useEffect, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface Props {
  url: string;
  digest?: string;
  pending: boolean;
  error: Error | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export function PortfolioConfirmation({ url, digest, pending, error, onConfirm, onCancel }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <section className="flex flex-col gap-2 rounded-md border border-border p-3">
      <h3 ref={heading} tabIndex={-1} className="font-semibold">
        {t(digest ? "portfolio.confirmTitle" : "portfolio.confirmWithdraw")}
      </h3>
      <p>{t(digest ? "portfolio.publicEffect" : "portfolio.withdrawEffect")}</p>
      <p className="break-all">{url}</p>
      {digest && <p className="break-all font-mono text-sm">{t("portfolio.digest", { digest })}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" disabled={pending} onClick={onCancel}>
          {t("portfolio.cancel")}
        </Button>
        <Button type="button" disabled={pending} onClick={onConfirm}>
          {t(digest ? "portfolio.confirmPublish" : "portfolio.removeNow")}
        </Button>
      </div>
      {error && <InlineError message={errorMessage(error)} />}
    </section>
  );
}
