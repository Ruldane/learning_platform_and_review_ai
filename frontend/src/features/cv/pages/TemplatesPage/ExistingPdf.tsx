import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { DocumentOut } from "../../types";

interface ExistingPdfProps {
  documents: DocumentOut[];
  value: string;
  disabled: boolean;
  onChange: (documentId: string) => void;
}

/** Pick a PDF already imported instead of sending another; nothing if there is none. */
export function ExistingPdf({ documents, value, disabled, onChange }: ExistingPdfProps) {
  const id = useId();
  if (documents.length === 0) return null;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("cv.templatesPage.existingLabel")}
      </label>
      <select
        id={id}
        className={fieldClass}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{t("cv.templatesPage.existingNone")}</option>
        {documents.map((doc) => (
          <option key={doc.id} value={doc.id}>
            {doc.name}
          </option>
        ))}
      </select>
    </div>
  );
}
