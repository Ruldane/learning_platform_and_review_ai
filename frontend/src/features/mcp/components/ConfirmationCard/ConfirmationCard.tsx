import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fullDateTime } from "@/shared/lib/relativeTime";
import { Button } from "@/shared/ui/button";
import type { ConfirmationView } from "../viewTypes";
import { VerdictBlock } from "./VerdictBlock";

interface ConfirmationCardProps {
  confirmation: ConfirmationView;
  /** Une décision est en cours : les deux boutons attendent la réponse. */
  busy: boolean;
  onConfirm: () => void;
  onRefuse: () => void;
}

/** La ligne de date qui convient à l'état : l'échéance tant que la demande attend. */
function dateLine({ state, expiresAt, decidedAt }: ConfirmationView): string {
  if (state === "pending") return t("mcp.confirmations.expires", { date: fullDateTime(expiresAt) });
  if (state === "expired")
    return t("mcp.confirmations.expiredOn", { date: fullDateTime(expiresAt) });
  return decidedAt ? t("mcp.confirmations.decided", { date: fullDateTime(decidedAt) }) : "";
}

/**
 * Une demande « À confirmer » : ce que Claude veut faire en résumé neutre, le verdict du contrôle
 * d'honnêteté, l'échéance. « Confirmer » et « Refuser » n'existent que tant qu'elle attend :
 * expirée, refusée ou déjà exécutée, elle ne se rejoue jamais.
 */
export function ConfirmationCard({
  confirmation,
  busy,
  onConfirm,
  onRefuse,
}: ConfirmationCardProps) {
  const headingId = useId();
  const { state, summary, action, tokenLabel, verdict } = confirmation;
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
