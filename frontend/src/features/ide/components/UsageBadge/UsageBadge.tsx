import { t } from "@/shared/i18n/t";
import type { UsageView } from "../viewTypes";

interface UsageBadgeProps {
  usage: UsageView;
}

const NUMBER = new Intl.NumberFormat("en-GB");

/**
 * What the teacher has used: tokens for the session and the day against their caps. The mode
 * « Sur demande » (cap reached or chosen) is written out in full: the teacher only replies
 * on its own, only when called.
 */
export function UsageBadge({ usage }: UsageBadgeProps) {
  return (
    <div
      role="group"
      aria-label={t("ide.usage.label")}
      className="flex flex-col gap-1 rounded-xl border border-border bg-card p-3 text-sm"
    >
      <p className="tabular-nums">
        {t("ide.usage.session", {
          used: NUMBER.format(usage.sessionTokens),
          cap: NUMBER.format(usage.sessionCap),
        })}
      </p>
      <p className="tabular-nums">
        {t("ide.usage.day", {
          used: NUMBER.format(usage.dayTokens),
          cap: NUMBER.format(usage.dayCap),
        })}
      </p>
      {usage.onDemand ? (
        <p className="font-medium">
          <span className="rounded border border-border px-1.5">{t("ide.usage.onDemand")}</span>{" "}
          <span className="font-normal text-muted-foreground">{t("ide.usage.onDemandHint")}</span>
        </p>
      ) : null}
    </div>
  );
}
