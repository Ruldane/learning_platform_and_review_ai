import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import type { SearchProviderName } from "../viewTypes";

interface ProviderRowProps {
  provider: SearchProviderName;
  /** Rang affiché, à partir de 1. */
  rank: number;
  /** Brave sans clé : ligne grisée, consigne affichée. */
  greyed: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

/** Une ligne de l'ordre des fournisseurs, avec ses deux boutons monter / descendre. */
export function ProviderRow({
  provider,
  rank,
  greyed,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
}: ProviderRowProps) {
  const name = t(`settings.search.order.${provider}`);
  return (
    <li
      aria-disabled={greyed || undefined}
      className={cn(
        "flex items-center gap-2 rounded-lg border border-border px-2.5 py-1.5 text-sm",
        greyed && "bg-muted text-muted-foreground",
      )}
    >
      <span aria-hidden="true" className="w-4 text-muted-foreground">
        {rank}.
      </span>
      <span className="font-medium">{name}</span>
      {greyed && <span className="text-xs">{t("settings.search.order.braveNeedsKey")}</span>}
      <span className="ml-auto flex gap-1">
        <Button
          type="button"
          variant="outline"
          size="icon-xs"
          aria-label={t("settings.search.order.up", { provider: name })}
          disabled={!canMoveUp}
          onClick={onMoveUp}
        >
          <span aria-hidden="true">↑</span>
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon-xs"
          aria-label={t("settings.search.order.down", { provider: name })}
          disabled={!canMoveDown}
          onClick={onMoveDown}
        >
          <span aria-hidden="true">↓</span>
        </Button>
      </span>
    </li>
  );
}
