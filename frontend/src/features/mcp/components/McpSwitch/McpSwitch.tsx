import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

interface McpSwitchProps {
  enabled: boolean;
  /** Une écriture est en cours : le bouton ne bouge plus avant la réponse. */
  pending: boolean;
  onChange: (enabled: boolean) => void;
}

/**
 * L'interrupteur général : coupé, aucun jeton n'ouvre rien. Le texte dit clairement ce que chaque
 * état ouvre ou ferme ; l'état est écrit en toutes lettres, jamais porté par la seule couleur.
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
