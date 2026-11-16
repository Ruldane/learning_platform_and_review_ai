import { ScreenshotPreview } from "./ScreenshotPreview";

interface ScreenshotListProps {
  files: File[];
  disabled: boolean;
  onRemove: (index: number) => void;
}

/** Une clé par fichier choisi, indépendante de sa place : en retirer un ne remonte pas les autres. */
const keys = new WeakMap<File, number>();
let nextKey = 0;
const keyOf = (file: File): number => {
  let key = keys.get(file);
  if (key === undefined) {
    key = nextKey;
    nextKey += 1;
    keys.set(file, key);
  }
  return key;
};

/** Les captures choisies, une ligne chacune avec son aperçu ; rien n'est rendu sans capture. */
export function ScreenshotList({ files, disabled, onRemove }: ScreenshotListProps) {
  if (files.length === 0) return null;
  return (
    <ul className="mt-1 flex flex-col gap-2">
      {files.map((file, index) => (
        <ScreenshotPreview
          key={keyOf(file)}
          file={file}
          disabled={disabled}
          onRemove={() => onRemove(index)}
        />
      ))}
    </ul>
  );
}
