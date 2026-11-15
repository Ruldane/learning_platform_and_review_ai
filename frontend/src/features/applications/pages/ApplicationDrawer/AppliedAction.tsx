import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DraftField, type FieldSpec } from "../../components/DraftField";
import { todayString } from "../../dates";
import type { EventIn } from "../../types";

const DAY: FieldSpec = { key: "day", label: t("applications.drawer.appliedDate"), kind: "date" };

interface AppliedActionProps {
  pending: boolean;
  onRecord: (event: EventIn) => Promise<boolean>;
}

/** « J'ai postulé » : le statut Postulée à la date choisie (aujourd'hui par défaut). */
export function AppliedAction({ pending, onRecord }: AppliedActionProps) {
  const [day, setDay] = useState(() => todayString());

  function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || day === "") return;
    void onRecord({ kind: "status", status: "applied", on: day });
  }

  return (
    <form noValidate onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <DraftField spec={DAY} value={day} onChange={setDay} />
      <Button type="submit" disabled={pending || day === ""}>
        {t("applications.drawer.appliedAction")}
      </Button>
    </form>
  );
}
