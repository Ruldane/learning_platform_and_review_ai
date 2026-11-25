import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

interface McpSwitchProps {
  enabled: boolean;
  /** A write is in progress: the button does not move until the answer. */
  pending: boolean;
  onChange: (enabled: boolean) => void;
}

/**
 * The master switch: off, no token opens anything. The text says clearly what each
 * state opens or closes; the state is written out in full, never carried by colour alone.
 */
export function McpSwitch({ enabled, pending, onChange }: McpSwitchProps) {
  const textId = useId();
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-describedby={textId}
          disabled={pending}
          onClick={() => onChange(!enabled)}
          className={cn(
            "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border border-border outline-none transition-colors",
            "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring disabled:opacity-50",
            enabled ? "bg-primary" : "bg-muted",
          )}
        >
          <span className="sr-only">{t("mcp.switch.label")}</span>
          <span
            aria-hidden="true"
            className={cn(
              "size-4 rounded-full bg-background shadow transition-transform",
              enabled ? "translate-x-6" : "translate-x-1",
            )}
          />
        </button>
        <span className="font-medium">{enabled ? t("mcp.switch.on") : t("mcp.switch.off")}</span>
      </div>
      <p id={textId} className="max-w-prose text-sm">
        {enabled ? t("mcp.switch.onText") : t("mcp.switch.offText")}
      </p>
      <p className="text-sm text-muted-foreground">{t("mcp.switch.hint")}</p>
    </div>
  );
}
