import { t } from "@/shared/i18n/t";

interface Props {
  value: string;
  onChange: (text: string) => void;
  disabled: boolean;
}

export function SystemDesignDefense({ value, onChange, disabled }: Props) {
  return (
    <label className="flex flex-col gap-2 font-medium">
      {t("systemDesign.defense")}
      <textarea
        className="min-h-28 rounded-md border border-input bg-background p-3 font-normal"
        maxLength={4000}
        required
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
      />
    </label>
  );
}
