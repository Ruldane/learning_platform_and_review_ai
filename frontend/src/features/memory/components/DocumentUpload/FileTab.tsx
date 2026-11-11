import { useState, type ChangeEvent } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { MAX_UPLOAD_BYTES, UPLOAD_EXTENSIONS } from "../format";

interface FileTabProps {
  busy: boolean;
  onUploadFile: (file: File) => void;
}

/** Vérification de courtoisie côté client ; le serveur impose les mêmes limites. */
function problemWith(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!UPLOAD_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return t("memory.upload.badType");
  }
  return file.size > MAX_UPLOAD_BYTES ? t("memory.upload.tooBig") : null;
}

/** Choix d'un fichier : refusé ici, sans appel, s'il dépasse 20 Mo ou n'est pas d'un type admis. */
export function FileTab({ busy, onUploadFile }: FileTabProps) {
  const [problem, setProblem] = useState<string | null>(null);

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const refusal = problemWith(file);
    setProblem(refusal);
    // Le champ est vidé : choisir à nouveau le même fichier déclenche bien un nouveau `change`.
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
