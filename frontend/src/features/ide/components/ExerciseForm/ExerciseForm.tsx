import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { ExerciseDraft, GenerateDraft } from "../viewTypes";
import { GenerateExerciseForm } from "./GenerateExerciseForm";
import { ManualExerciseForm } from "./ManualExerciseForm";

interface ExerciseFormProps {
  creating: boolean;
  generating: boolean;
  /** Un message de réussite (« Exercice ajouté. »), annoncé sans prendre le focus. */
  notice: string | null;
  /** L'erreur du serveur, en français. */
  error: string | null;
  onCreate: (draft: ExerciseDraft) => Promise<boolean>;
  onGenerate: (draft: GenerateDraft) => void;
}

/**
 * Deux façons d'avoir un exercice : l'écrire (énoncé, code de départ, tests) ou le faire
 * générer par les agents (sujet, niveau).
 */
export function ExerciseForm(props: ExerciseFormProps) {
  const headingId = useId();
  const { creating, generating, notice, error, onCreate, onGenerate } = props;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-4">
      <h2 id={headingId} className="text-lg font-medium">
        {t("ide.form.title")}
      </h2>
      <div className="grid gap-6 lg:grid-cols-2">
        <ManualExerciseForm pending={creating} onCreate={onCreate} />
        <GenerateExerciseForm pending={generating} onGenerate={onGenerate} />
      </div>
      <p role="status" className="text-sm">
        {notice}
      </p>
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </section>
  );
}
