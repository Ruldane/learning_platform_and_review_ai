import { useId, type ChangeEvent } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { PdfChoice } from "../viewTypes";
import { pdfProblem } from "./pdfProblem";

interface PdfPickerProps {
  label: string;
  disabled: boolean;
  /** Ce qui est retenu (gardé par la page) : un fichier, ou la raison de son refus. */
  choice: PdfChoice;
  onChange: (choice: PdfChoice) => void;
}

/**
 * Un champ de fichier PDF : un fichier refusé n'est jamais gardé, son message s'affiche dessous.
 * Le fichier retenu est écrit sous le champ, qui se vide quand l'étape est quittée puis revue.
 */
export function PdfPicker({ label, disabled, choice, onChange }: PdfPickerProps) {
  const id = useId();
  const change = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    const problem = file ? pdfProblem(file) : null;
    onChange({ file: problem === null ? file : null, problem });
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
        aria-invalid={choice.problem !== null}
        aria-describedby={choice.problem ? `${id}-problem` : undefined}
        className={`${fieldClass} h-auto py-1.5`}
      />
      {choice.file ? (
        <p className="text-sm text-muted-foreground">
          {t("onboarding.cv.chosen", { name: choice.file.name })}
        </p>
      ) : null}
      {choice.problem ? (
        <p id={`${id}-problem`} role="alert" className="text-sm text-destructive">
          {choice.problem}
        </p>
      ) : null}
    </div>
  );
}
