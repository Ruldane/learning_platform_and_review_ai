import { useId } from "react";
import { Button } from "@/shared/ui/button";
import type { ConfirmationView } from "../viewTypes";
import { ConfirmationFields } from "./ConfirmationFields";
import { useConfirmationValues } from "./useConfirmationValues";

interface ConfirmationCardProps {
  confirmation: ConfirmationView;
  /** Faux quand la question est déjà répondue ou qu'une réponse part. */
  disabled?: boolean;
  /** Une issue choisie, avec les champs tels que January les laisse (seulement pour créer). */
  onChoose: (choice: string, fields: Record<string, string>) => void;
}

/** Les issues qui enregistrent une fiche : seules elles envoient les champs relus. */
const WRITES = ["create", "distinct"];

/**
 * La fiche que l'Assistant de suivi a lue dans la phrase, à confirmer : un champ par information,
 * déjà rempli et modifiable, puis les issues du serveur (créer, c'est un autre poste, ouvrir la
 * fiche existante, annuler). Créer exige les champs obligatoires ; ouvrir et annuler restent
 * toujours possibles. La date vide se lit « aujourd'hui ».
 */
export function ConfirmationCard({
  confirmation,
  disabled = false,
  onChoose,
}: ConfirmationCardProps) {
  const questionId = useId();
  const { values, setValue, complete, roleWithoutName } = useConfirmationValues(confirmation);
  const choose = (choice: string) => onChoose(choice, WRITES.includes(choice) ? { ...values } : {});

  return (
    <section
      aria-labelledby={questionId}
      className="flex flex-col gap-3 rounded-xl border-2 border-primary bg-card px-4 py-3"
    >
      <p id={questionId} className="font-medium">
        {confirmation.question}
      </p>
      {confirmation.reason ? (
        <p role="alert" className="text-sm text-destructive">
          {confirmation.reason}
        </p>
      ) : null}
      <ConfirmationFields
        confirmation={confirmation}
        values={values}
        disabled={disabled}
        roleWithoutName={roleWithoutName}
        onChange={setValue}
      />
      <div className="flex flex-wrap gap-2">
        {confirmation.options.map((option) => (
          <Button
            key={option.value}
            type="button"
            variant={option.value === "create" ? "default" : "outline"}
            disabled={disabled || (WRITES.includes(option.value) && !complete)}
            onClick={() => choose(option.value)}
          >
            {option.label}
          </Button>
        ))}
      </div>
    </section>
  );
}
