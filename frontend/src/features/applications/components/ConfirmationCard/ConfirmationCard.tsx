import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ConfirmationFieldView, ConfirmationView } from "../viewTypes";
import { DraftField, type FieldKind } from "../DraftField";
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

/** La nature d'un champ : statut, canal, date et notes ont leur propre commande, le reste est du texte. */
const KINDS: Record<string, FieldKind> = {
  status: "status",
  channel: "channel",
  applied_on: "date",
  notes: "textarea",
};

function specOf(field: ConfirmationFieldView, value: string) {
  const todayHint = field.id === "applied_on" && value === "";
  return {
    key: field.id,
    label: field.label,
    kind: KINDS[field.id] ?? "text",
    required: field.required,
    maxLength: field.maxLength,
    hint: todayHint ? t("applications.confirm.todayHint") : undefined,
  };
}

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
  const { values, setValue, complete } = useConfirmationValues(confirmation);
  const choose = (choice: string) => onChoose(choice, WRITES.includes(choice) ? { ...values } : {});

  return (
    <section
      aria-labelledby={questionId}
      className="flex flex-col gap-3 rounded-xl border-2 border-primary bg-card px-4 py-3"
    >
      <p id={questionId} className="font-medium">
        {confirmation.question}
      </p>
      <div
        role="group"
        aria-label={t("applications.confirm.label")}
        className="grid gap-3 sm:grid-cols-2"
      >
        {confirmation.fields.map((field, index) => (
          <DraftField
            key={field.id}
            spec={specOf(field, values[field.id] ?? "")}
            value={values[field.id] ?? ""}
            disabled={disabled}
            autoFocus={!disabled && index === 0}
            onChange={(value) => setValue(field.id, value)}
          />
        ))}
      </div>
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
