import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DraftField, statusChoices, type FieldSpec } from "../../components/DraftField";
import { todayString } from "../../dates";
import { isStatus, type EventIn, type StatusView } from "../../types";

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
 * Changes the record's status on a date (today by default); for « Entretien », the date of
 * the interview can be given. The current status is not offered (« même statut »: no effect).
 */
export function StatusChange({ current, pending, onRecord }: StatusChangeProps) {
  const others = statusChoices().filter((choice) => choice.value !== current);
  const [status, setStatus] = useState(others[0]?.value ?? current);
  const [day, setDay] = useState(() => todayString());
  const [interviewOn, setInterviewOn] = useState("");
  const [refused, setRefused] = useState(false);
  const today = todayString();
  const future = day > today;

  function submit(event: FormEvent) {
    event.preventDefault();
    setRefused(true);
    if (pending || day === "" || future || !isStatus(status)) return;
    const body: EventIn = { kind: "status", status, on: day };
    if (status === "interview" && interviewOn !== "") body.interview_on = interviewOn;
    void onRecord(body);
  }

  return (
    <form noValidate onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <DraftField spec={STATUS} value={status} options={others} onChange={setStatus} />
      <DraftField
        spec={{ ...DAY, max: today }}
        value={day}
        error={refused && future ? t("applications.fields.futureDate") : undefined}
        onChange={setDay}
      />
      {status === "interview" ? (
        <DraftField spec={INTERVIEW} value={interviewOn} onChange={setInterviewOn} />
      ) : null}
      <Button type="submit" variant="outline" disabled={pending || day === ""}>
        {t("applications.drawer.statusAction")}
      </Button>
    </form>
  );
}
