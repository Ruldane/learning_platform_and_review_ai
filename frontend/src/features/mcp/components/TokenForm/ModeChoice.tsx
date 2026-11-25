import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { TokenMode } from "../viewTypes";

interface ModeChoiceProps {
  value: TokenMode;
  onChange: (mode: TokenMode) => void;
}

const MODES = [
  { mode: "read", label: "mcp.form.modeRead", hint: "mcp.form.modeReadHint" },
  { mode: "write", label: "mcp.form.modeWrite", hint: "mcp.form.modeWriteHint" },
] as const;

/** Read only or read and write: read only is chosen by default. */
export function ModeChoice({ value, onChange }: ModeChoiceProps) {
  const prefix = useId();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium">{t("mcp.form.mode")}</legend>
      {MODES.map(({ mode, label, hint }) => (
        <div key={mode} className="flex items-start gap-2">
          <input
            id={`${prefix}-${mode}`}
            type="radio"
            name={`${prefix}-mode`}
            className="mt-1"
            checked={value === mode}
            aria-describedby={`${prefix}-${mode}-hint`}
            onChange={() => onChange(mode)}
          />
          <div className="flex flex-col">
            <label htmlFor={`${prefix}-${mode}`} className="text-sm font-medium">
              {t(label)}
            </label>
            <span id={`${prefix}-${mode}-hint`} className="text-xs text-muted-foreground">
              {t(hint)}
            </span>
          </div>
        </div>
      ))}
    </fieldset>
  );
}
