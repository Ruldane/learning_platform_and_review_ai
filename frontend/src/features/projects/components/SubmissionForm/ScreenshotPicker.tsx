import { useId, useState, type ChangeEvent } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { pickScreenshots, SCREENSHOT_TYPES } from "./rules";
import { ScreenshotList } from "./ScreenshotList";

interface ScreenshotPickerProps {
  files: File[];
  disabled: boolean;
  /** Le refus du serveur pour les captures (format que ses octets ne confirment pas, trop de captures). */
  error?: string;
  onChange: (files: File[]) => void;
}

/** Choisir jusqu'à 5 captures (PNG, JPEG, WebP, 5 Mo) : une capture refusée n'est jamais gardée. */
export function ScreenshotPicker({ files, disabled, error, onChange }: ScreenshotPickerProps) {
  const id = useId();
  const [problems, setProblems] = useState<string[]>([]);

  const pick = (event: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = "";
    const { kept, problems: found } = pickScreenshots(files, picked);
    setProblems(found);
    onChange(kept);
  };

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("projects.submission.screenshots")}
      </label>
      <input
        id={id}
        type="file"
        multiple
        accept={SCREENSHOT_TYPES.join(",")}
        disabled={disabled}
        onChange={pick}
        aria-describedby={`${id}-hint`}
        aria-invalid={problems.length > 0 || error !== undefined}
        className={`${fieldClass} h-auto py-1.5`}
      />
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {t("projects.submission.screenshotsHint")}
      </p>
      {problems.map((problem) => (
        <p key={problem} role="alert" className="text-sm text-destructive">
          {problem}
        </p>
      ))}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <ScreenshotList
        files={files}
        disabled={disabled}
        onRemove={(index) => {
          setProblems([]);
          onChange(files.filter((_, position) => position !== index));
        }}
      />
    </div>
  );
}
