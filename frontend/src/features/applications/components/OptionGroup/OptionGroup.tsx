import { useId } from "react";

export interface OptionView {
  value: string;
  label: string;
  /** Une phrase qui précise le choix : lue avec lui. */
  hint?: string;
}

interface OptionGroupProps {
  legend: string;
  /** Le nom commun des boutons radio (un groupe par nom). */
  name: string;
  options: OptionView[];
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}

/** Un choix parmi quelques-uns : des boutons radio natifs dans un groupe nommé (flèches du clavier comprises). */
export function OptionGroup({
  legend,
  name,
  options,
  value,
  disabled,
  onChange,
}: OptionGroupProps) {
  const prefix = useId();
  return (
    <fieldset className="flex flex-col gap-2" disabled={disabled}>
      <legend className="mb-1 text-sm font-medium">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const id = `${prefix}-${option.value}`;
          return (
            <div
              key={option.value}
              className="flex min-w-40 flex-1 items-start gap-2 rounded-lg border bg-card px-3 py-2 has-[:checked]:border-primary has-[:checked]:ring-1 has-[:checked]:ring-primary has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring"
            >
              <input
                id={id}
                type="radio"
                name={`${prefix}-${name}`}
                value={option.value}
                checked={option.value === value}
                aria-describedby={option.hint ? `${id}-hint` : undefined}
                onChange={() => onChange(option.value)}
                className="mt-1"
              />
              <div className="flex flex-col">
                <label htmlFor={id} className="text-sm font-medium">
                  {option.label}
                </label>
                {option.hint ? (
                  <span id={`${id}-hint`} className="text-xs text-muted-foreground">
                    {option.hint}
                  </span>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
