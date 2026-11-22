import { useQuery } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import { fetchTargetPrograms } from "../../api";
import { gapKeys } from "../../queryKeys";

interface ProgramPickerProps {
  value?: string;
  onChange: (value: string | undefined) => void;
  disabled: boolean;
}

export function ProgramPicker({ value, onChange, disabled }: ProgramPickerProps) {
  const { data: programs } = useQuery({
    queryKey: gapKeys.targetPrograms,
    queryFn: ({ signal }) => fetchTargetPrograms(signal),
  });
  if (!programs?.length) return null;
  return (
    <label className="flex max-w-md flex-col gap-1 text-sm font-medium">
      {t("gap.table.targetProgram")}
      <select
        className="rounded-md border bg-background px-3 py-2"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value || undefined)}
        disabled={disabled}
      >
        <option value="">{t("gap.table.latestProgram")}</option>
        {programs.map((program) => (
          <option key={program.id} value={program.id}>
            {program.title}
          </option>
        ))}
      </select>
    </label>
  );
}
