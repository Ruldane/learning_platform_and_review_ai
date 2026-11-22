interface Props {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}

export function NumberField({ label, value, min, max, onChange }: Props) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span>{label}</span>
      <input
        className="min-w-0 rounded-md border border-input bg-background p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        type="number"
        min={min}
        max={max}
        step={1}
        required
        value={Number.isFinite(value) ? value : ""}
        onChange={(event) => onChange(event.currentTarget.valueAsNumber)}
      />
    </label>
  );
}
