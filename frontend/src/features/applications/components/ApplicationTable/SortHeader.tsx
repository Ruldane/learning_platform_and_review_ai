import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { SortDirection } from "./sort";

interface SortHeaderProps {
  label: string;
  /** Absent : la colonne n'est pas celle du tri. */
  direction?: SortDirection;
  onSort: () => void;
}

/** L'en-tête d'une colonne triable : `aria-sort` sur la cellule, le clic sur le bouton qu'elle contient. */
export function SortHeader({ label, direction, onSort }: SortHeaderProps) {
  const Icon =
    direction === "ascending" ? ArrowUp : direction === "descending" ? ArrowDown : ChevronsUpDown;
  return (
    <th scope="col" aria-sort={direction ?? "none"} className="px-3 py-2 text-left font-medium">
      <button
        type="button"
        aria-label={t("applications.table.sortBy", { column: label })}
        onClick={onSort}
        className="inline-flex items-center gap-1 rounded outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring"
      >
        {label}
        <Icon aria-hidden="true" className="size-3.5 text-muted-foreground" />
      </button>
    </th>
  );
}
