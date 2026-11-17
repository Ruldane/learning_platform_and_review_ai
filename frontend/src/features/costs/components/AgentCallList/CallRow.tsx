import { t } from "@/shared/i18n/t";
import { formatCallTime, formatCount, formatLatency, formatUsd } from "../format";
import type { CallView } from "../viewTypes";
import { SessionCell } from "./SessionCell";

const NUMERIC = "px-3 py-2 text-right tabular-nums whitespace-nowrap";

/**
 * Un appel : instant, agent, parcours, modèle, jetons, durée, coût (« estimé » signalé), session.
 */
export function CallRow({ call }: { call: CallView }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="px-3 py-2 whitespace-nowrap">
        <time dateTime={call.at}>{formatCallTime(call.at)}</time>
      </td>
      <td className="px-3 py-2">
        <span className="inline-flex items-center gap-2">
          {call.agentColor ? (
            <span
              aria-hidden="true"
              className="size-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: call.agentColor }}
            />
          ) : null}
          {call.agentLabel}
        </span>
      </td>
      <td className="px-3 py-2">{call.graphLabel}</td>
      <td className="px-3 py-2 whitespace-nowrap">{call.model}</td>
      <td className={NUMERIC}>{formatCount(call.tokensIn)}</td>
      <td className={NUMERIC}>{formatCount(call.tokensOut)}</td>
      <td className={NUMERIC}>{formatLatency(call.latencyMs)}</td>
      <td className={NUMERIC}>
        {formatUsd(call.costUsd)}
        {call.estimated ? (
          <span className="ml-1.5 rounded border border-border px-1 text-xs text-muted-foreground">
            {t("costs.estimatedTag")}
          </span>
        ) : null}
      </td>
      <td className="px-3 py-2">
        <SessionCell call={call} />
      </td>
    </tr>
  );
}
