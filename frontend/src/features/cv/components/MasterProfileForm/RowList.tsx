import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { FactSourceBadges } from "../FactSourceBadges";
import type { FactSourceView } from "../viewTypes";
import { removeAt, replaceAt } from "./profileDraft";

interface RowListProps<T extends { sources: FactSourceView[] }> {
  items: T[];
  onChange: (items: T[]) => void;
  blank: () => T;
  /** « Expérience 2 »: the row name, the legend of its group. */
  rowName: (n: number) => string;
  addLabel: string;
  removeLabel: (n: number) => string;
  /** The fields of row `index`; `patch` changes some of them without touching the others. */
  children: (item: T, index: number, patch: (changes: Partial<T>) => void) => ReactNode;
}

/**
 * A list of profile rows (experiences, education, skills…): each row is a named group with
 * its sources as badges and its « Retirer » button; « Ajouter » adds an empty one.
 */
export function RowList<T extends { sources: FactSourceView[] }>({
  items,
  onChange,
  blank,
  rowName,
  addLabel,
  removeLabel,
  children,
}: RowListProps<T>) {
  return (
    <>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("cv.profile.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((item, index) => (
            <li key={index}>
              <fieldset className="flex flex-col gap-3 rounded-lg border p-3">
                <legend className="flex items-center gap-2 px-1 text-sm font-medium">
                  {rowName(index + 1)}
                  <FactSourceBadges sources={item.sources} />
                </legend>
                {children(item, index, (changes) => onChange(replaceAt(items, index, changes)))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="self-start"
                  onClick={() => onChange(removeAt(items, index))}
                >
                  {removeLabel(index + 1)}
                </Button>
              </fieldset>
            </li>
          ))}
        </ul>
      )}
      <Button
        type="button"
        variant="secondary"
        className="self-start"
        onClick={() => onChange([...items, blank()])}
      >
        {addLabel}
      </Button>
    </>
  );
}
