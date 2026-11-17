import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface NameFieldProps {
  value: string;
  onChange: (value: string) => void;
}

/** Le nom du jeton : de quoi le reconnaître dans la liste (60 caractères au plus). */
export function NameField({ value, onChange }: NameFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("mcp.form.name")}
      </label>
      <input
        id={id}
        type="text"
        maxLength={60}
        autoComplete="off"
        placeholder={t("mcp.form.namePlaceholder")}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={fieldClass}
      />
    </div>
  );
}
