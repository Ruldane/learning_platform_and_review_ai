import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface StyleGuideEditorProps {
  value: string;
  /** Refusé par le serveur : le texte n'est jamais cité, seulement le champ. */
  refused?: boolean;
  onChange: (value: string) => void;
}

/** Le guide de style personnel : un texte libre et le nombre de caractères écrits. */
export function StyleGuideEditor({ value, refused = false, onChange }: StyleGuideEditorProps) {
  const id = useId();
  const hintId = useId();
  const count = [...value].length;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("settings.style.label")}
      </label>
      <textarea
        id={id}
        value={value}
        rows={12}
        aria-invalid={refused}
        aria-describedby={hintId}
        onChange={(event) => onChange(event.target.value)}
        className={`${fieldClass} h-auto min-h-48 py-2 leading-relaxed`}
      />
      <p id={hintId} className="flex flex-wrap justify-between gap-2 text-sm text-muted-foreground">
        <span className={refused ? "text-destructive" : undefined}>
          {refused ? t("settings.fields.refused") : t("settings.style.hint")}
        </span>
        <span>
          {t(count === 1 ? "settings.style.countOne" : "settings.style.count", { count })}
        </span>
      </p>
    </div>
  );
}
