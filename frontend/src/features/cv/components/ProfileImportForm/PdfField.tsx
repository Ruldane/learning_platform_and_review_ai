import { useId, useState, type ChangeEvent } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";
import { pdfProblem } from "./pdfProblem";

interface PdfFieldProps {
  label: string;
  hint?: string;
  disabled: boolean;
  /** The chosen file, or `null` when it is refused or removed. */
  onPick: (file: File | null) => void;
}

/** A PDF file field: a refused file is never kept, its message shows below it. */
export function PdfField({ label, hint, disabled, onPick }: PdfFieldProps) {
  const id = useId();
  const [problem, setProblem] = useState<string | null>(null);
  const change = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    const message = file ? pdfProblem(file) : null;
    setProblem(message);
    onPick(message === null ? file : null);
  };
  const describedBy = [hint ? `${id}-hint` : null, problem ? `${id}-problem` : null]
    .filter(Boolean)
    .join(" ");
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
        aria-describedby={describedBy || undefined}
        className={`${fieldClass} h-auto py-1.5`}
      />
      {hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {problem ? (
        <p id={`${id}-problem`} role="alert" className="text-sm text-destructive">
          {problem}
        </p>
      ) : null}
    </div>
  );
}
