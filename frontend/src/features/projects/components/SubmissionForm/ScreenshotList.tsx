import { ScreenshotPreview } from "./ScreenshotPreview";

interface ScreenshotListProps {
  files: File[];
  disabled: boolean;
  onRemove: (index: number) => void;
}

/** One key per chosen file, independent of its place: removing one does not shift the others. */
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

/** The chosen screenshots, one row each with its preview; nothing renders with none. */
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
