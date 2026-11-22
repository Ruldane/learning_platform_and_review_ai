import { t } from "@/shared/i18n/t";
import type { Draft } from "../../api";

type Indicator = Pick<Draft, "indicator" | "unit" | "target" | "due_on">;
type Props = { draft: Indicator; onChange: (field: keyof Indicator, value: string) => void };

const fields = [
  { key: "indicator", label: "datedCommitments.indicator", type: "text", maxLength: 160 },
  { key: "unit", label: "datedCommitments.unit", type: "text", maxLength: 40 },
  {
    key: "target",
    label: "datedCommitments.target",
    type: "text",
    inputMode: "decimal",
    maxLength: 32,
  },
  { key: "due_on", label: "datedCommitments.dueOn", type: "date" },
] as const;

export function IndicatorFields({ draft, onChange }: Props) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {fields.map(({ key, label, ...options }) => (
        <label key={key} className="flex min-w-0 flex-col gap-1">
          {t(label)}
          <input
            {...options}
            required
            value={draft[key]}
            onChange={(event) => onChange(key, event.target.value)}
            className="rounded border border-border bg-background p-2"
          />
        </label>
      ))}
    </div>
  );
}
