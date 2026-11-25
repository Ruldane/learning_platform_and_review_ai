import { useState, type ChangeEvent, type DragEvent } from "react";
import { t } from "@/shared/i18n/t";
import { fileProblem } from "../source";

/**
 * Choosing or dropping a file: a file of an unsupported type or too large is refused here
 * (`problem`), with no call; otherwise `onFile` receives it.
 */
export function useFilePicker(disabled: boolean, onFile: (file: File) => void) {
  const [problem, setProblem] = useState<string | null>(null);
  const [over, setOver] = useState(false);

  const accept = (file: File | undefined) => {
    if (!file) return;
    const refusal = fileProblem(file);
    setProblem(refusal ? t(`capture.input.${refusal}`) : null);
    if (!refusal) onFile(file);
  };
  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    accept(event.target.files?.[0]);
    // Cleared: choosing the same file again does fire a new `change`.
    event.target.value = "";
  };
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setOver(false);
    if (!disabled) accept(event.dataTransfer.files[0]);
  };
  const onDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setOver(true);
  };
  return { problem, over, onChange, onDrop, onDragOver, onDragLeave: () => setOver(false) };
}
