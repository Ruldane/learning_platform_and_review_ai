import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { JournalKindView } from "../viewTypes";

const KINDS: readonly JournalKindView[] = ["capture", "study_session", "quiz", "weekly_review"];

interface KindFilterProps {
  /** `null` : tous les types. */
  value: JournalKindView | null;
  onChange: (kind: JournalKindView | null) => void;
}

/** Le filtre par type d'entrée : une liste déroulante native (clavier et lecteurs d'écran d'office). */
export function KindFilter({ value, onChange }: KindFilterProps) {
  const id = useId();
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {t("capture.journal.filter.label")}
      </label>
      <select
        id={id}
        value={value ?? ""}
        onChange={(event) =>
          onChange(event.target.value === "" ? null : (event.target.value as JournalKindView))
        }
        className={`${fieldClass} w-auto`}
      >
        <option value="">{t("capture.journal.filter.all")}</option>
        {KINDS.map((kind) => (
          <option key={kind} value={kind}>
            {t(`capture.journal.filter.${kind}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
