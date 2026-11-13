import { useState, type ChangeEvent, type DragEvent } from "react";
import { t } from "@/shared/i18n/t";
import { fileProblem } from "../source";

/**
 * Le choix ou le dépôt d'un fichier : un fichier d'un type non admis ou trop gros est refusé ici
 * (`problem`), sans appel ; sinon `onFile` le reçoit.
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
    // Vidé : choisir à nouveau le même fichier déclenche bien un nouveau `change`.
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
