import { t } from "@/shared/i18n/t";
import type { SearchProviderName } from "../viewTypes";
import { ProviderRow } from "./ProviderRow";

interface ProviderOrderEditorProps {
  value: SearchProviderName[];
  /** Une clé Brave existe : sans elle, Brave est grisé et l'ordre n'est pas modifiable. */
  braveAvailable: boolean;
  onChange: (order: SearchProviderName[]) => void;
}

function swap(order: SearchProviderName[], from: number, to: number): SearchProviderName[] {
  const a = order[from];
  const b = order[to];
  if (a === undefined || b === undefined) return order;
  const next = [...order];
  next[from] = b;
  next[to] = a;
  return next;
}

/** Ordre de repli des fournisseurs de recherche : monter / descendre (pas de glisser-déposer). */
export function ProviderOrderEditor({ value, braveAvailable, onChange }: ProviderOrderEditorProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium">{t("settings.search.order.label")}</span>
      <p className="text-xs text-muted-foreground">{t("settings.search.order.hint")}</p>
      <ol className="flex flex-col gap-2">
        {value.map((provider, index) => (
          <ProviderRow
            key={provider}
            provider={provider}
            rank={index + 1}
            greyed={provider === "brave" && !braveAvailable}
            canMoveUp={braveAvailable && index > 0}
            canMoveDown={braveAvailable && index < value.length - 1}
            onMoveUp={() => onChange(swap(value, index, index - 1))}
            onMoveDown={() => onChange(swap(value, index, index + 1))}
          />
        ))}
      </ol>
    </div>
  );
}
