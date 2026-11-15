import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DraftField, statusChoices, type FieldSpec } from "../../components/DraftField";
import { todayString } from "../../dates";
import type { EventIn, StatusView } from "../../types";

const STATUS: FieldSpec = {
  key: "status",
  label: t("applications.drawer.statusSelect"),
  kind: "status",
};
const DAY: FieldSpec = { key: "day", label: t("applications.drawer.statusDate"), kind: "date" };
const INTERVIEW: FieldSpec = {
  key: "interview",
  label: t("applications.drawer.statusInterviewDate"),
  kind: "date",
};

interface StatusChangeProps {
  current: StatusView;
  pending: boolean;
  onRecord: (event: EventIn) => Promise<boolean>;
}

/**
 * Changer le statut de la fiche à une date (aujourd'hui par défaut) ; pour « Entretien », la date de
 * l'entretien peut être donnée. Le statut actuel n'est pas proposé (« même statut » : sans effet).
 */
export function StatusChange({ current, pending, onRecord }: StatusChangeProps) {
  const others = statusChoices().filter((choice) => choice.value !== current);
  const [status, setStatus] = useState(others[0]?.value ?? current);
  const [day, setDay] = useState(() => todayString());
  const [interviewOn, setInterviewOn] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || day === "") return;
    const body: EventIn = { kind: "status", status: status as StatusView, on: day };
    if (status === "interview" && interviewOn !== "") body.interview_on = interviewOn;
    void onRecord(body);
  }

  return (
    <form noValidate onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <DraftField spec={STATUS} value={status} options={others} onChange={setStatus} />
      <DraftField spec={DAY} value={day} onChange={setDay} />
      {status === "interview" ? (
        <DraftField spec={INTERVIEW} value={interviewOn} onChange={setInterviewOn} />
      ) : null}
      <Button type="submit" variant="outline" disabled={pending || day === ""}>
        {t("applications.drawer.statusAction")}
      </Button>
    </form>
  );
}
