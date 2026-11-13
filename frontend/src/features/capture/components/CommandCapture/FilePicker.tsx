import { Upload } from "lucide-react";
import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { InlineError } from "@/shared/ui/states/InlineError";
import { FILE_EXTENSIONS } from "../source";
import { useFilePicker } from "./useFilePicker";

interface FilePickerProps {
  disabled: boolean;
  onFile: (file: File) => void;
}

/**
 * Dépôt ou choix d'un fichier. Le champ natif reste accessible au clavier ; le dépôt n'est qu'un
 * raccourci à la souris.
 */
export function FilePicker({ disabled, onFile }: FilePickerProps) {
  const id = useId();
  const picker = useFilePicker(disabled, onFile);
  return (
    <div
      onDragOver={picker.onDragOver}
      onDragLeave={picker.onDragLeave}
      onDrop={picker.onDrop}
      className={cn(
        "flex flex-col items-center gap-2 rounded-xl border border-dashed px-4 py-4 text-center text-sm",
        picker.over ? "border-primary bg-muted" : "border-border",
      )}
    >
      <Upload aria-hidden="true" className="size-4 text-muted-foreground" />
      <p>{t("capture.input.drop")}</p>
      <input
        id={id}
        type="file"
        accept={FILE_EXTENSIONS.join(",")}
        disabled={disabled}
        onChange={picker.onChange}
        className="peer sr-only"
      />
      <label
        htmlFor={id}
        className="rounded font-medium underline underline-offset-4 peer-focus-visible:ring-3 peer-focus-visible:ring-ring"
      >
        {t("capture.input.chooseFile")}
      </label>
      <p className="text-xs text-muted-foreground">{t("capture.input.fileHint")}</p>
      {picker.problem ? <InlineError message={picker.problem} /> : null}
    </div>
  );
}
