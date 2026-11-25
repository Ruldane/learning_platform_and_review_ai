import { useState, type FormEvent, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { HoursField } from "./HoursField";
import { MessageField } from "./MessageField";

/** Contract bounds: 60 to 10,080 minutes, i.e. 1 h to 168 h. */
const MIN_HOURS = 1;
const MAX_HOURS = 168;

export interface ReplanRequestView {
  /** Minutes available this week; `null`: the budget does not change. */
  availableMinutes: number | null;
  message: string | null;
}

interface ReplanFormProps {
  busy: boolean;
  launchMenu?: ReactNode;
  /** Message for a server refusal (draft, unknown program…). */
  error: string | null;
  onSubmit: (request: ReplanRequestView) => void;
}

/** The hours typed (comma or point) in minutes; `NaN` if unreadable, `null` if empty. */
function minutesOf(hours: string): number | null {
  const text = hours.trim().replace(",", ".");
  if (text === "") return null;
  const value = Number(text);
  return Number.isFinite(value) && value >= MIN_HOURS && value <= MAX_HOURS
    ? Math.round(value * 60)
    : Number.NaN;
}

/** The starting form: hours available this week and a message to the Strategist, both optional. */
export function ReplanForm({ busy, error, onSubmit, launchMenu }: ReplanFormProps) {
  const [hours, setHours] = useState("");
  const [message, setMessage] = useState("");
  const [invalid, setInvalid] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    const minutes = minutesOf(hours);
    setInvalid(Number.isNaN(minutes));
    if (Number.isNaN(minutes)) return;
    onSubmit({ availableMinutes: minutes, message: message.trim() === "" ? null : message.trim() });
  };

  return (
    <form onSubmit={submit} aria-label={t("replan.form.label")} className="flex flex-col gap-3">
      <HoursField value={hours} invalid={invalid} disabled={busy} onChange={setHours} />
      <MessageField value={message} disabled={busy} onChange={setMessage} />
      {error ? <InlineError message={error} /> : null}
      {launchMenu}
      <Button type="submit" disabled={busy} className="self-start">
        {busy ? t("replan.form.submitting") : t("replan.form.submit")}
      </Button>
    </form>
  );
}
