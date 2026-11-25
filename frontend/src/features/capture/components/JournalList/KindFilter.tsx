import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { JournalKindView } from "../viewTypes";

const KINDS: readonly JournalKindView[] = [
  "capture",
  "study_session",
  "quiz",
  "ide_check",
  "weekly_review",
  "project",
];

interface KindFilterProps {
  /** `null`: all types. */
  value: JournalKindView | null;
  onChange: (kind: JournalKindView | null) => void;
}

/** The filter by entry type: a native dropdown (keyboard and screen readers by default). */
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
