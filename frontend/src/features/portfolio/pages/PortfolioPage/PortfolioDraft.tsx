import { useEffect, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { Draft, Publication } from "../../api";
import { PortfolioConfirmation } from "./PortfolioConfirmation";

import { PortfolioPreview } from "./PortfolioPreview";
import { useDraftPublication } from "./useDraftPublication";

interface Props {
  value: Draft;
  current: Publication | null;
  reload: () => void;
}

export function PortfolioDraft({ value, current, reload }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  const { trigger, approval, setApproval, preview, zip, launch, cancel } = useDraftPublication(
    value,
    reload,
  );
  useEffect(() => heading.current?.focus(), []);
  const active = current?.revision_id === value.id && current?.available === true;
  return (
    <section className="flex flex-col gap-3">
      <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">
        {t("portfolio.preview")}
      </h2>
      <PortfolioPreview busy={preview.isPending} error={preview.error} html={preview.data} />
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={zip.isPending}
          onClick={() => zip.mutate()}
        >
          {t("portfolio.zip")}
        </Button>
        {value.destination && preview.data && !active && !approval && (
          <Button ref={trigger} type="button" onClick={() => setApproval(value.destination)}>
            {t(current ? "portfolio.replace" : "portfolio.reviewPublish")}
          </Button>
        )}
      </div>
      {zip.error && <InlineError message={errorMessage(zip.error)} />}
      {!value.destination && <p>{t("portfolio.hostUnavailable")}</p>}
      {approval && (
        <PortfolioConfirmation
          url={approval}
          digest={value.digest}
          pending={launch.isPending}
          error={launch.error}
          onConfirm={() => launch.mutate(approval)}
          onCancel={cancel}
        />
      )}
    </section>
  );
}
