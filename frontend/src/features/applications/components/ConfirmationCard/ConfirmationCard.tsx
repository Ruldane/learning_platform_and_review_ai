import { useId } from "react";
import { Button } from "@/shared/ui/button";
import type { ConfirmationView } from "../viewTypes";
import { ConfirmationFields } from "./ConfirmationFields";
import { useConfirmationValues } from "./useConfirmationValues";

interface ConfirmationCardProps {
  confirmation: ConfirmationView;
  /** False when the question is already answered or an answer is being sent. */
  disabled?: boolean;
  /** A chosen outcome, with the fields as January leaves them (only for creating). */
  onChoose: (choice: string, fields: Record<string, string>) => void;
}

/** The outcomes that save a record: only these send the re-read fields. */
const WRITES = ["create", "distinct"];

/**
 * The record the tracking Assistant read from the sentence, to confirm: one field per piece of
 * information,
 * already filled in and editable, then the server's outcomes (create means another posting,
 * open the existing record, cancel). Creating requires the mandatory fields; opening and
 * cancelling stay still possible. An empty date reads « aujourd'hui ».
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
