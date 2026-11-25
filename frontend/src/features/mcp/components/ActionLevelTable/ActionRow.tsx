import { t } from "@/shared/i18n/t";
import type { ActionView } from "../viewTypes";

/** A tool: name, feature, level, type, role, and what calls for caution. */
export function ActionRow({ action }: { action: ActionView }) {
  return (
    <tr className="border-b border-border align-top last:border-0">
      <td className="px-3 py-2 font-mono">{action.name}</td>
      <td className="px-3 py-2">{action.featureLabel}</td>
      <td className="px-3 py-2 whitespace-nowrap">{t(`mcp.level.l${action.level}`)}</td>
      <td className="px-3 py-2">{t(`mcp.levels.kind.${action.kind}`)}</td>
      <td className="px-3 py-2">
        {action.summary}
        {action.external ? (
          <p className="text-xs text-muted-foreground">{t("mcp.levels.external")}</p>
        ) : null}
        {action.untrusted ? (
          <p className="text-xs text-muted-foreground">{t("mcp.levels.untrusted")}</p>
        ) : null}
      </td>
    </tr>
  );
}
