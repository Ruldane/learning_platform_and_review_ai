import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface RoleInputProps {
  id: string;
  value: string;
  disabled: boolean;
  onChange: (role: string) => void;
}

/** L'intitulé d'un poste à saisir, pour un entretien sans fiche ni offre. */
export function RoleInput({ id, value, disabled, onChange }: RoleInputProps) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-sm font-medium">
      {t("applications.interviewSetup.target.roleLabel")}
      <input
        id={id}
        type="text"
        value={value}
        maxLength={200}
        disabled={disabled}
        aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(event.target.value)}
        className={fieldClass}
      />
      <span id={`${id}-hint`} className="text-xs font-normal text-muted-foreground">
        {t("applications.interviewSetup.target.roleHint")}
      </span>
    </label>
  );
}
