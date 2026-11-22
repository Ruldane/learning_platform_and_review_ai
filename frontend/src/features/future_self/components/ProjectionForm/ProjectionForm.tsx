import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ProjectionChoices } from "../viewTypes";
import { CapacityFields } from "./CapacityFields";
import { Field } from "./Field";

type Props = {
  role: string | null;
  zone: string;
  target: number;
  onCompare: (choices: ProjectionChoices) => void;
};

export function ProjectionForm({ role, zone, target, onCompare }: Props) {
  const [draftRole, setRole] = useState<string>();
  const [draftZone, setZone] = useState<string>();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const hours = fields.get("hours");
    onCompare({
      role: (draftRole ?? role)?.trim() || undefined,
      zone: (draftZone ?? zone).trim() || undefined,
      hours: hours === "" ? undefined : Number(hours),
      target: Number(fields.get("target")),
    });
  }

  return (
    <form className="grid gap-4 rounded-xl border bg-card p-4 sm:grid-cols-2" onSubmit={submit}>
      <Field
        label={t("futureSelf.role")}
        value={draftRole ?? role ?? ""}
        onChange={(event) => setRole(event.currentTarget.value)}
        minLength={2}
        maxLength={120}
      />
      <Field
        label={t("futureSelf.zone")}
        value={draftZone ?? zone}
        onChange={(event) => setZone(event.currentTarget.value)}
        minLength={2}
        maxLength={120}
      />
      <CapacityFields target={target} />
      <Button className="justify-self-start" type="submit">
        {t("futureSelf.submit")}
      </Button>
    </form>
  );
}
