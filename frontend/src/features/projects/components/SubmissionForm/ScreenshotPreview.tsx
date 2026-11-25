import { useEffect, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ScreenshotPreviewProps {
  file: File;
  disabled: boolean;
  onRemove: () => void;
}

/** Preview of a chosen screenshot, with its « Retirer » button; read by `FileReader`. */
export function ScreenshotPreview({ file, disabled, onRemove }: ScreenshotPreviewProps) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    // A preview read as a `data:` URL needs no cleanup, and is safe under `StrictMode`.
    const reader = new FileReader();
    reader.onload = () => setSrc(typeof reader.result === "string" ? reader.result : null);
    reader.readAsDataURL(file);
    return () => reader.abort();
  }, [file]);
  return (
    <li className="flex items-center gap-3 rounded-lg border bg-background p-2 text-sm">
      {src ? (
        <img
          src={src}
          alt={t("projects.submission.preview", { name: file.name })}
          className="size-14 rounded object-cover"
        />
      ) : null}
      <span className="min-w-0 flex-1 truncate">{file.name}</span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={disabled}
        aria-label={t("projects.submission.remove", { name: file.name })}
        onClick={onRemove}
      >
        {t("projects.submission.removeShort")}
      </Button>
    </li>
  );
}
