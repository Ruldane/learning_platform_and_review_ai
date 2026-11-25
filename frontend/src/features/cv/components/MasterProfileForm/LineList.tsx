import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { LineView } from "../viewTypes";
import { Field } from "./Field";
import { blank, removeAt, replaceAt } from "./profileDraft";

interface LineListProps {
  /** Path of the list (`experiences.0.achievements`); each row adds `.<n>.text`. */
  path: string;
  /** Name of the row that holds them (« Expérience 1 »), for accessible names. */
  context: string;
  lines: LineView[];
  onChange: (lines: LineView[]) => void;
  lineLabel: (n: number) => string;
  addLabel: string;
  addAriaLabel: string;
  removeAriaLabel: (n: number) => string;
}

/** Text lines of an entry (achievements, details): one area per line, with add and remove. */
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
