import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { HoursField } from "./HoursField";
import { MessageField } from "./MessageField";

/** Bornes du contrat : 60 à 10 080 minutes, soit 1 h à 168 h. */
const MIN_HOURS = 1;
const MAX_HOURS = 168;

export interface ReplanRequestView {
  /** Minutes disponibles cette semaine ; `null` : le budget ne change pas. */
  availableMinutes: number | null;
  message: string | null;
}

interface ReplanFormProps {
  busy: boolean;
  /** Message d'un refus du serveur (brouillon, programme inconnu…). */
  error: string | null;
  onSubmit: (request: ReplanRequestView) => void;
}

/** Les heures saisies (virgule ou point) en minutes ; `NaN` si illisible, `null` si vide. */
function minutesOf(hours: string): number | null {
  const text = hours.trim().replace(",", ".");
  if (text === "") return null;
  const value = Number(text);
  return Number.isFinite(value) && value >= MIN_HOURS && value <= MAX_HOURS
    ? Math.round(value * 60)
    : Number.NaN;
}

/** Le formulaire de départ : heures disponibles cette semaine et message au Stratège, tous deux facultatifs. */
export function ReplanForm({ busy, error, onSubmit }: ReplanFormProps) {
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
      <Button type="submit" disabled={busy} className="self-start">
        {busy ? t("replan.form.submitting") : t("replan.form.submit")}
      </Button>
    </form>
  );
}
