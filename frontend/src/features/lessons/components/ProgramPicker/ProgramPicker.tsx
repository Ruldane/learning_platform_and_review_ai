import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ProgramOption } from "../viewTypes";

interface ProgramPickerProps {
  programs: ProgramOption[];
  value: string;
  onChange: (programId: string) => void;
}

/** Picks the program whose lessons are read (dropdown, newest first). */
export function ProgramPicker({ programs, value, onChange }: ProgramPickerProps) {
  return (
    <label className="flex max-w-md flex-col gap-1 text-sm font-medium">
      {t("lessons.filters.program")}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={fieldClass}
      >
        {programs.map((program) => (
          <option key={program.id} value={program.id}>
            {program.title}
          </option>
        ))}
      </select>
    </label>
  );
}
