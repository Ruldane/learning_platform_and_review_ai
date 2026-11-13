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
  /** « Expérience 2 » : nom de la ligne, légende de son groupe. */
  rowName: (n: number) => string;
  addLabel: string;
  removeLabel: (n: number) => string;
  /** Les champs de la ligne `index` ; `patch` en change certains sans toucher aux autres. */
  children: (item: T, index: number, patch: (changes: Partial<T>) => void) => ReactNode;
}

/**
 * Une liste de lignes du profil (expériences, formations, compétences…) : chaque ligne est un
 * groupe nommé avec ses sources en badges et son bouton « Retirer » ; « Ajouter » en pose une vide.
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
