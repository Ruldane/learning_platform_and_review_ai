import { useId, useState, type ChangeEvent } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";
import { pdfProblem } from "./pdfProblem";

interface PdfPickerProps {
  label: string;
  disabled: boolean;
  /** Le fichier choisi, ou `null` quand il est refusé ou retiré. */
  onPick: (file: File | null) => void;
}

/** Un champ de fichier PDF : un fichier refusé n'est jamais gardé, son message s'affiche dessous. */
export function PdfPicker({ label, disabled, onPick }: PdfPickerProps) {
  const id = useId();
  const [problem, setProblem] = useState<string | null>(null);
  const change = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    const message = file ? pdfProblem(file) : null;
    setProblem(message);
    onPick(message === null ? file : null);
  };
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type="file"
        accept=".pdf,application/pdf"
        disabled={disabled}
        onChange={change}
        aria-invalid={problem !== null}
        aria-describedby={problem ? `${id}-problem` : undefined}
        className={`${fieldClass} h-auto py-1.5`}
      />
      {problem ? (
        <p id={`${id}-problem`} role="alert" className="text-sm text-destructive">
          {problem}
        </p>
      ) : null}
    </div>
  );
}
