import { ScreenshotPreview } from "./ScreenshotPreview";

interface ScreenshotListProps {
  files: File[];
  disabled: boolean;
  onRemove: (index: number) => void;
}

/** Les captures choisies, une ligne chacune avec son aperçu ; rien n'est rendu sans capture. */
export function ScreenshotList({ files, disabled, onRemove }: ScreenshotListProps) {
  if (files.length === 0) return null;
  return (
    <ul className="mt-1 flex flex-col gap-2">
      {files.map((file, index) => (
        <ScreenshotPreview
          key={`${index}-${file.name}-${file.size}`}
          file={file}
          disabled={disabled}
          onRemove={() => onRemove(index)}
        />
      ))}
    </ul>
  );
}
