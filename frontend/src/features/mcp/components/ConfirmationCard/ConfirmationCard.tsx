import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fullDateTime } from "@/shared/lib/relativeTime";
import { Button } from "@/shared/ui/button";
import type { ConfirmationView } from "../viewTypes";
import { RequestBlock } from "./RequestBlock";
import { VerdictBlock } from "./VerdictBlock";

interface ConfirmationCardProps {
  confirmation: ConfirmationView;
  /** A decision is in progress: both buttons wait for the answer. */
  busy: boolean;
  onConfirm: () => void;
  onRefuse: () => void;
}

/** The date line that fits the state: the deadline while the request waits. */
function dateLine({ state, expiresAt, decidedAt }: ConfirmationView): string {
  if (state === "pending") return t("mcp.confirmations.expires", { date: fullDateTime(expiresAt) });
  if (state === "expired")
    return t("mcp.confirmations.expiredOn", { date: fullDateTime(expiresAt) });
  return decidedAt ? t("mcp.confirmations.decided", { date: fullDateTime(decidedAt) }) : "";
}

/**
 * A « À confirmer » request: what Claude wants to do, in a neutral summary, the honesty check
 * verdict, the deadline. « Confirmer » and « Refuser » exist only while it waits:
 * expired, refused or already run, it is never replayed.
 */
export function ConfirmationCard({
  confirmation,
  busy,
  onConfirm,
  onRefuse,
}: ConfirmationCardProps) {
  const headingId = useId();
  const { state, summary, action, tokenLabel, verdict, request } = confirmation;
  return (
    <article
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 id={headingId} className="max-w-prose font-medium">
          {summary}
        </h3>
        <span className="rounded border border-border px-1.5 text-xs">
          {t(`mcp.confirmations.status.${state}`)}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">
        {tokenLabel ? `${t("mcp.confirmations.by", { label: tokenLabel })} · ` : ""}
        {t("mcp.confirmations.action", { action })}
      </p>
      <RequestBlock request={request} />
      <VerdictBlock verdict={verdict} />
      {state === "failed" ? <p className="text-sm">{t("mcp.confirmations.failedText")}</p> : null}
      <p className="text-sm text-muted-foreground">{dateLine(confirmation)}</p>
      {state === "pending" ? (
        <div className="flex gap-2">
          <Button disabled={busy} aria-describedby={headingId} onClick={onConfirm}>
            {t("mcp.confirmations.confirm")}
          </Button>
          <Button variant="outline" disabled={busy} aria-describedby={headingId} onClick={onRefuse}>
            {t("mcp.confirmations.refuse")}
          </Button>
        </div>
      ) : null}
    </article>
  );
}
