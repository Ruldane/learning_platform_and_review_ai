import { useState, type FormEvent, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { RadarRunRequestView } from "../viewTypes";
import { TextField } from "./TextField";

/** Longueur minimale d'un poste ou d'une zone saisis (`RadarRunIn.minLength`). */
const MIN_LENGTH = 2;

interface RadarFormProps {
  /** Le poste proposé (réglage, sinon dernier objectif) ; modifiable. */
  role: string;
  /** La zone proposée ; modifiable, vide pour laisser le défaut du serveur. */
  zone: string;
  onRun: (request: RadarRunRequestView) => void;
  /** Un relevé est en cours : le bouton attend sa fin (un seul relevé à la fois). */
  running: boolean;
  launchMenu?: ReactNode;
  /** Le refus du serveur sur le poste (409 `radar_role_required`, 422), montré sur le champ. */
  roleError?: string;
  /** Le refus du serveur sur la zone (422), montré sur le champ. */
  zoneError?: string;
}

interface FieldErrors {
  role?: string;
  zone?: string;
}

/** Le poste est obligatoire ; la zone peut rester vide (défaut du serveur), mais pas faire 1 caractère. */
function validate(role: string, zone: string): FieldErrors {
  const errors: FieldErrors = {};
  if (role === "") errors.role = t("radar.form.roleRequired");
  else if (role.length < MIN_LENGTH) errors.role = t("radar.form.roleTooShort");
  if (zone !== "" && zone.length < MIN_LENGTH) errors.zone = t("radar.form.zoneTooShort");
  return errors;
}

function useRadarFields({ role, zone, onRun, running, roleError, zoneError }: RadarFormProps) {
  const [roleValue, setRoleValue] = useState(role);
  const [zoneValue, setZoneValue] = useState(zone);
  const [attempted, setAttempted] = useState(false);
  // Un refus du serveur sur un champ s'efface dès que ce champ est modifié ; un nouvel envoi le
  // remontre s'il revient.
  const [dismissed, setDismissed] = useState<FieldErrors>({});
  const local = attempted ? validate(roleValue.trim(), zoneValue.trim()) : {};

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (running) return;
    const [trimmedRole, trimmedZone] = [roleValue.trim(), zoneValue.trim()];
    setAttempted(true);
    setDismissed({});
    if (Object.keys(validate(trimmedRole, trimmedZone)).length > 0) return;
    onRun({ role: trimmedRole, zone: trimmedZone || null });
  };

  return {
    submit,
    role: {
      value: roleValue,
      error: local.role ?? (roleError === dismissed.role ? undefined : roleError),
      onChange: (value: string) => {
        setRoleValue(value);
        setDismissed((previous) => ({ ...previous, role: roleError }));
      },
    },
    zone: {
      value: zoneValue,
      error: local.zone ?? (zoneError === dismissed.zone ? undefined : zoneError),
      onChange: (value: string) => {
        setZoneValue(value);
        setDismissed((previous) => ({ ...previous, zone: zoneError }));
      },
    },
  };
}

/** Les valeurs proposées ne sont lues qu'une fois : la page change la clé du formulaire. */
export function RadarForm(props: RadarFormProps) {
  const { running, launchMenu } = props;
  const fields = useRadarFields(props);
  return (
    <form
      onSubmit={fields.submit}
      noValidate
      aria-label={t("radar.form.label")}
      aria-busy={running}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <TextField label={t("radar.form.role")} disabled={running} {...fields.role} />
      <TextField label={t("radar.form.zone")} disabled={running} {...fields.zone} />
      <p className="text-xs text-muted-foreground">{t("radar.form.hint")}</p>
      {running ? null : launchMenu}
      <Button type="submit" className="self-start" aria-disabled={running}>
        {running ? t("radar.form.running") : t("radar.form.run")}
      </Button>
    </form>
  );
}
