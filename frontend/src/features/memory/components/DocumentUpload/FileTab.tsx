import { useState, type ChangeEvent } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { MAX_UPLOAD_BYTES, UPLOAD_EXTENSIONS } from "../format";

interface FileTabProps {
  busy: boolean;
  onUploadFile: (file: File) => void;
}

/** Client-side courtesy check; the server enforces the same limits. */
function problemWith(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!UPLOAD_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return t("memory.upload.badType");
  }
  return file.size > MAX_UPLOAD_BYTES ? t("memory.upload.tooBig") : null;
}

/** File choice: refused here, without a call, if it exceeds 20 MB or is not an allowed type. */
export function FileTab({ busy, onUploadFile }: FileTabProps) {
  const [problem, setProblem] = useState<string | null>(null);

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const refusal = problemWith(file);
    setProblem(refusal);
    // The field is emptied: choosing the same file again does fire a new `change`.
    event.target.value = "";
    if (!refusal) onUploadFile(file);
  };

  return (
    <>
      <label className="flex flex-col gap-1 text-sm font-medium">
        {t("memory.upload.chooseFile")}
        <input
          type="file"
          accept={UPLOAD_EXTENSIONS.join(",")}
          disabled={busy}
          onChange={onChange}
          className="text-sm font-normal file:mr-3 file:rounded-lg file:border file:border-border file:bg-background file:px-2.5 file:py-1 file:text-sm file:font-medium"
        />
      </label>
      <p className="text-sm text-muted-foreground">{t("memory.upload.fileHint")}</p>
      {problem ? <InlineError message={problem} /> : null}
    </>
  );
}
