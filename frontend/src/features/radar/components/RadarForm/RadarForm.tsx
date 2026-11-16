import { useState, type FormEvent } from "react";
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

/**
 * Lancer un relevé : poste (obligatoire, 2 caractères au moins) et zone (vide ou 2 caractères au
 * moins). Rien ne part tant qu'un champ est refusé ; les erreurs se corrigent en direct après le
 * premier essai. Les valeurs proposées ne sont lues qu'une fois : la page change la `key` du
 * formulaire quand elles arrivent.
 */
export function RadarForm({ role, zone, onRun, running, roleError, zoneError }: RadarFormProps) {
  const [roleValue, setRoleValue] = useState(role);
  const [zoneValue, setZoneValue] = useState(zone);
  const [attempted, setAttempted] = useState(false);
  const local = attempted ? validate(roleValue.trim(), zoneValue.trim()) : {};

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (running) return;
    const [trimmedRole, trimmedZone] = [roleValue.trim(), zoneValue.trim()];
    setAttempted(true);
    if (Object.keys(validate(trimmedRole, trimmedZone)).length > 0) return;
    onRun({ role: trimmedRole, zone: trimmedZone || null });
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={t("radar.form.label")}
      aria-busy={running}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <TextField
        label={t("radar.form.role")}
        value={roleValue}
        disabled={running}
        error={local.role ?? roleError}
        onChange={setRoleValue}
      />
      <TextField
        label={t("radar.form.zone")}
        value={zoneValue}
        disabled={running}
        error={local.zone ?? zoneError}
        onChange={setZoneValue}
      />
      <p className="text-xs text-muted-foreground">{t("radar.form.hint")}</p>
      <Button type="submit" className="self-start" disabled={running}>
        {running ? t("radar.form.running") : t("radar.form.run")}
      </Button>
    </form>
  );
}
