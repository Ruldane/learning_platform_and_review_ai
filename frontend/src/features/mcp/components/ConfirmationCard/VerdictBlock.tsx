import { CircleAlert, CircleCheck } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { VerdictView } from "../viewTypes";

/**
 * The honesty check verdict, spelled out (never colour alone). Without a check,
 * the card says so: no verdict is not an "all good".
 */
export function VerdictBlock({ verdict }: { verdict: VerdictView | null }) {
  if (!verdict) {
    return <p className="text-sm text-muted-foreground">{t("mcp.confirmations.precheckNone")}</p>;
  }
  const Icon = verdict.ok ? CircleCheck : CircleAlert;
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-background p-2 text-sm">
      <p className="flex items-center gap-1.5 font-medium">
        <Icon aria-hidden="true" className="size-4" />
        {t("mcp.confirmations.precheck")}
      </p>
      <p>
        {verdict.ok ? t("mcp.confirmations.precheckOk") : t("mcp.confirmations.precheckReserves")}
      </p>
      {verdict.reasons.length > 0 ? (
        <ul className="list-disc pl-5">
          {verdict.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
      {verdict.summary ? <p className="text-muted-foreground">{verdict.summary}</p> : null}
    </div>
  );
}
