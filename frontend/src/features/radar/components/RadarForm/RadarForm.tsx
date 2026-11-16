import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { RadarRunRequestView } from "../viewTypes";
import { TextField } from "./TextField";

interface RadarFormProps {
  /** Le poste proposé (réglage, sinon dernier objectif) ; modifiable. */
  role: string;
  /** La zone proposée ; modifiable, vide pour laisser le défaut du serveur. */
  zone: string;
  onRun: (request: RadarRunRequestView) => void;
  /** Un relevé est en cours : le bouton attend sa fin (un seul relevé à la fois). */
  running: boolean;
}

/** Lancer un relevé : poste (obligatoire) et zone. Rien ne part avec un poste vide. */
export function RadarForm({ role, zone, onRun, running }: RadarFormProps) {
  const [roleValue, setRoleValue] = useState(role);
  const [zoneValue, setZoneValue] = useState(zone);
  const [invalid, setInvalid] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (running) return;
    const trimmedRole = roleValue.trim();
    setInvalid(trimmedRole === "");
    if (trimmedRole === "") return;
    onRun({ role: trimmedRole, zone: zoneValue.trim() || null });
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
        error={invalid ? t("radar.form.roleRequired") : undefined}
        onChange={setRoleValue}
      />
      <TextField
        label={t("radar.form.zone")}
        value={zoneValue}
        disabled={running}
        onChange={setZoneValue}
      />
      <p className="text-xs text-muted-foreground">{t("radar.form.hint")}</p>
      <Button type="submit" className="self-start" disabled={running}>
        {running ? t("radar.form.running") : t("radar.form.run")}
      </Button>
    </form>
  );
}
