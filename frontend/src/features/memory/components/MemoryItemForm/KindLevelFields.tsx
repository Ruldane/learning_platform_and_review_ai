import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { NEW_KINDS, type Draft, type EditableLevel, type NewKind } from "./itemFormModel";

interface KindLevelFieldsProps {
  draft: Draft;
  chooseKind: boolean;
  withLevel: boolean;
  disabled: boolean;
  onChange: (patch: Partial<Draft>) => void;
}

const LEVELS: readonly EditableLevel[] = ["declare", "en_cours"];

/** Choix du type (création seulement) et du niveau (acquis déclaré ou en cours seulement). */
export function KindLevelFields({
  draft,
  chooseKind,
  withLevel,
  disabled,
  onChange,
}: KindLevelFieldsProps) {
  return (
    <div className="flex flex-wrap gap-3">
      {chooseKind ? (
        <label className="flex flex-col gap-1 text-sm font-medium">
          {t("memory.form.kind")}
          <select
            value={draft.kind}
            disabled={disabled}
            onChange={(e) => onChange({ kind: e.target.value as NewKind })}
            className={fieldClass}
          >
            {NEW_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {t(`memory.kind.${kind}`)}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {withLevel ? (
        <label className="flex flex-col gap-1 text-sm font-medium">
          {t("memory.form.level")}
          <select
            value={draft.level}
            disabled={disabled}
            onChange={(e) => onChange({ level: e.target.value as EditableLevel })}
            className={fieldClass}
          >
            {LEVELS.map((level) => (
              <option key={level} value={level}>
                {t(`memory.level.${level}`)}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </div>
  );
}
