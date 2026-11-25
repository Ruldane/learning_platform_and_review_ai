import { useState, type FormEvent, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { RadarRunRequestView } from "../viewTypes";
import { TextField } from "./TextField";

/** Minimum length of a typed role or area (`RadarRunIn.minLength`). */
const MIN_LENGTH = 2;

interface RadarFormProps {
  /** The suggested role (setting, else last goal); editable. */
  role: string;
  /** The suggested area; editable, empty to keep the server default. */
  zone: string;
  onRun: (request: RadarRunRequestView) => void;
  /** A sweep is running: the button waits for its end (one sweep at a time). */
  running: boolean;
  launchMenu?: ReactNode;
  /** The server's refusal on the role (409 `radar_role_required`, 422), shown on the field. */
  roleError?: string;
  /** The server's refusal on the area (422), shown on the field. */
  zoneError?: string;
}

interface FieldErrors {
  role?: string;
  zone?: string;
}

/** The role is required; the area may stay empty (server default), but not be 1 character. */
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
  // A server refusal on a field clears as soon as that field is edited; a new send the
  // shows it again if it comes back.
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

/** The suggested values are read only once: the page changes the form's key. */
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
