import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ProofChoice } from "../viewTypes";

interface Props {
  proofs: ProofChoice[];
  busy: boolean;
  onSchedule: (proofId: string, day: string) => void;
}

export function ScheduleForm({ proofs, busy, onSchedule }: Props) {
  const proofField = useId();
  const dayField = useId();
  const [choice, setChoice] = useState("");
  const [date, setDate] = useState("");
  const proof = proofs.find((item) => item.id === choice);
  if (proofs.length === 0) return <p>{t("skillTransfer.noProof")}</p>;
  return (
    <form
      className="grid gap-3 rounded-xl border bg-card p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (proof && date) onSchedule(proof.id, date);
      }}
    >
      <label htmlFor={proofField} className="text-sm font-medium">{t("skillTransfer.proof")}</label>
      <select
        className={fieldClass}
        id={proofField}
        value={proof?.id ?? ""}
        onChange={(event) => setChoice(event.target.value)}
        required
      >
        <option value="">{t("skillTransfer.chooseProof")}</option>
        {proofs.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
      <label htmlFor={dayField} className="text-sm font-medium">{t("skillTransfer.dueOn")}</label>
      <input
        id={dayField}
        className={fieldClass}
        type="date"
        value={date}
        onChange={(event) => setDate(event.target.value)}
        required
      />
      <Button className="justify-self-start" type="submit" disabled={!proof || !date || busy}>
        {t("skillTransfer.schedule")}
      </Button>
    </form>
  );
}
