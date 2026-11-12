import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { BoardStateView } from "../boardTypes";

interface BoardStateListProps {
  states: readonly BoardStateView[];
  activeId: string;
  onSelect: (id: string) => void;
}

/** Les états enregistrés du tableau, du plus ancien au plus récent : titre, type, auteur. */
export function BoardStateList({ states, activeId, onSelect }: BoardStateListProps) {
  const ordered = [...states].sort((a, b) => a.step - b.step);
  return (
    <nav aria-label={t("session.board.states")}>
      <ol className="flex flex-col gap-1">
        {ordered.map((state) => {
          const active = state.id === activeId;
          return (
            <li key={state.id}>
              <button
                type="button"
                aria-current={active ? "true" : undefined}
                onClick={() => onSelect(state.id)}
                className={cn(
                  "flex w-full flex-col items-start rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:bg-muted motion-reduce:transition-none",
                  active ? "border-primary bg-muted" : "border-transparent",
                )}
              >
                <span className="font-medium">{state.title}</span>{" "}
                <span className="text-xs text-muted-foreground">
                  {t("session.board.stateMeta", {
                    kind: t(`session.board.kinds.${state.kind}`),
                    author: t(`session.board.authors.${state.author}`),
                  })}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
