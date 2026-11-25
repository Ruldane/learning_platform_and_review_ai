import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { ApplicationPatch, EventIn, StatusView } from "../../types";

/**
 * A write to the record (status, note or field edit) and the announcement of what just
 * changed, read by a live region: « Statut changé : Postulée. », « Note ajoutée. » or « Fiche
 * enregistrée. ». Nothing is announced if the server refuses. The announcement sits outside the
 * form, which
 * remounts when the record is re-read.
 */
export function useRecordMessage(
  current: StatusView,
  writes: {
    record: (event: EventIn) => Promise<boolean>;
    save: (patch: ApplicationPatch) => Promise<boolean>;
  },
) {
  const [message, setMessage] = useState("");
  async function recordAndSay(event: EventIn): Promise<boolean> {
    setMessage("");
    const done = await writes.record(event);
    if (!done) return false;
    const status = t(`applications.status.${event.status ?? current}`);
    setMessage(
      event.kind === "note"
        ? t("applications.drawer.noteAdded")
        : t("applications.drawer.statusChanged", { status }),
    );
    return true;
  }
  async function saveAndSay(patch: ApplicationPatch): Promise<boolean> {
    setMessage("");
    const done = await writes.save(patch);
    if (done) setMessage(t("applications.drawer.saved"));
    return done;
  }
  return { message, recordAndSay, saveAndSay };
}
