import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ListProps } from "./types";

export function ConversationEntries({
  entries,
  selected,
  busy,
  onSelect,
}: Pick<ListProps, "entries" | "selected" | "busy" | "onSelect">) {
  return (
    <ul className="flex max-h-64 flex-col gap-1 overflow-auto">
      {entries.map(({ id, title }) => (
        <li key={id}>
          <Button
            type="button"
            aria-label={t("conversations.list.open", { title })}
            aria-current={id === selected ? "true" : undefined}
            disabled={busy}
            variant={id === selected ? "secondary" : "ghost"}
            size="sm"
            className="w-full justify-start overflow-hidden"
            onClick={() => onSelect(id)}
          >
            <span className="truncate">{title}</span>
          </Button>
        </li>
      ))}
    </ul>
  );
}
