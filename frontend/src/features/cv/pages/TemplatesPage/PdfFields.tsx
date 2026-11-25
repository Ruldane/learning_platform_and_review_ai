import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { DocumentOut } from "../../types";
import { ExistingPdf } from "./ExistingPdf";

export const FILE_FIELD_ID = "template-file";

interface PdfFieldsProps {
  disabled: boolean;
  fileChosen: boolean;
  imported: DocumentOut[];
  documentId: string;
  onFile: (file: File | null) => void;
  onDocument: (documentId: string) => void;
}

/** Where the PDF comes from: a file to send, or a PDF already imported (a list, if there is one). */
export function PdfFields({
  disabled,
  fileChosen,
  imported,
  documentId,
  onFile,
  onDocument,
}: PdfFieldsProps) {
  const hintId = useId();
  return (
    <>
      <div className="flex flex-col gap-1">
        <label htmlFor={FILE_FIELD_ID} className="text-sm font-medium">
          {t("cv.templatesPage.file")}
        </label>
        <input
          id={FILE_FIELD_ID}
          type="file"
          accept="application/pdf,.pdf"
          disabled={disabled}
          aria-describedby={hintId}
          onChange={(event) => onFile(event.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <span id={hintId} className="text-xs text-muted-foreground">
          {t("cv.templatesPage.fileHint")}
        </span>
      </div>
      <ExistingPdf
        documents={imported}
        value={documentId}
        disabled={disabled || fileChosen}
        onChange={onDocument}
      />
    </>
  );
}
