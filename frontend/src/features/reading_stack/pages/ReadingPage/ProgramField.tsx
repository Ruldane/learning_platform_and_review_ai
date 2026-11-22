import { t } from "@/shared/i18n/t";

interface ProgramFieldProps {
  programs?: readonly { id: string; title: string }[];
  value: string;
  onChange: (value: string) => void;
}

export function ProgramField({ programs, value, onChange }: ProgramFieldProps) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {t("reading.actions.program")}
      <select
        className="rounded-md border bg-background p-2"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{t("reading.actions.chooseProgram")}</option>
        {programs?.map((program) => (
          <option key={program.id} value={program.id}>
            {program.title}
          </option>
        ))}
      </select>
    </label>
  );
}
