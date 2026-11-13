import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { LineView } from "../viewTypes";
import { Field } from "./Field";
import { blank, removeAt, replaceAt } from "./profileDraft";

interface LineListProps {
  /** Chemin de la liste (`experiences.0.achievements`) ; chaque ligne ajoute `.<n>.text`. */
  path: string;
  /** Nom de la ligne qui les porte (« Expérience 1 »), pour les noms accessibles. */
  context: string;
  lines: LineView[];
  onChange: (lines: LineView[]) => void;
  lineLabel: (n: number) => string;
  addLabel: string;
  addAriaLabel: string;
  removeAriaLabel: (n: number) => string;
}

/** Les lignes de texte d'une entrée (réalisations, détails) : une zone par ligne, ajout et retrait. */
export function LineList({
  path,
  context,
  lines,
  onChange,
  lineLabel,
  addLabel,
  addAriaLabel,
  removeAriaLabel,
}: LineListProps) {
  return (
    <div className="flex flex-col gap-2">
      {lines.map((line, index) => (
        <div key={index} className="flex items-start gap-2">
          <div className="flex-1">
            <Field
              path={`${path}.${index}.text`}
              label={lineLabel(index + 1)}
              context={context}
              value={line.text}
              multiline
              onChange={(text) => onChange(replaceAt(lines, index, { text }))}
            />
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-6 shrink-0"
            aria-label={removeAriaLabel(index + 1)}
            onClick={() => onChange(removeAt(lines, index))}
          >
            {t("cv.profile.removeLine")}
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="self-start"
        aria-label={addAriaLabel}
        onClick={() => onChange([...lines, blank.line()])}
      >
        {addLabel}
      </Button>
    </div>
  );
}
