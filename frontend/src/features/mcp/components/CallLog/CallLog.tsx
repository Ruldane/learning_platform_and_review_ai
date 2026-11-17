import { t } from "@/shared/i18n/t";
import { fullDateTime } from "@/shared/lib/relativeTime";
import type { CallView } from "../viewTypes";

const COLUMNS = ["at", "action", "token", "level", "code", "duration"] as const;

/** Le journal des appels : l'outil, le niveau, le code et la durée, jamais le contenu. */
export function CallLog({ calls }: { calls: CallView[] }) {
  if (calls.length === 0) {
    return <p className="text-muted-foreground">{t("mcp.history.callsEmpty")}</p>;
  }
  return (
    <div
      role="region"
      aria-label={t("mcp.history.calls")}
      tabIndex={0}
      className="overflow-x-auto rounded-xl border border-border bg-card"
    >
      <table className="w-full text-sm">
        <caption className="sr-only">{t("mcp.history.calls")}</caption>
        <thead className="border-b border-border text-left">
          <tr>
            {COLUMNS.map((column) => (
              <th key={column} scope="col" className="px-3 py-2 font-medium">
                {t(`mcp.history.columns.${column}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calls.map((call) => (
            <tr key={call.id} className="border-b border-border last:border-0">
              <td className="px-3 py-2 whitespace-nowrap">
                <time dateTime={call.at}>{fullDateTime(call.at)}</time>
              </td>
              <td className="px-3 py-2 font-mono">{call.action}</td>
              <td className="px-3 py-2">{call.tokenLabel ?? t("mcp.history.unknownToken")}</td>
              <td className="px-3 py-2">{t(`mcp.level.l${call.level}`)}</td>
              <td className="px-3 py-2 tabular-nums">{call.code}</td>
              <td className="px-3 py-2 whitespace-nowrap tabular-nums">
                {t("mcp.history.duration", { ms: call.durationMs })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
