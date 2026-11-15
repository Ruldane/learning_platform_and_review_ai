import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { ApplicationPatch, EventIn, StatusView } from "../../types";

/**
 * Une écriture sur la fiche (statut, note ou retouche des champs) et l'annonce de ce qui vient de
 * changer, lue par une zone vocale : « Statut changé : Postulée. », « Note ajoutée. » ou « Fiche
 * enregistrée. ». Rien n'est annoncé si le serveur refuse. L'annonce vit hors du formulaire, qui est
 * remonté quand la fiche est relue.
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
