import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ApplicationDetail, ApplicationPatch } from "../../types";
import { changesOf, problemOf, toDraft, type DetailsDraft } from "./detailsDraft";
import { DetailsFields } from "./DetailsFields";

interface DetailsFormProps {
  detail: ApplicationDetail;
  pending: boolean;
  /** Envoie ce qui a changé (et annonce « Fiche enregistrée. » hors du formulaire, qui est remonté). */
  onSave: (patch: ApplicationPatch) => Promise<boolean>;
}

/**
 * Les champs modifiables de la fiche et ses contacts, enregistrés d'un coup (`PATCH`, seulement ce
 * qui a changé). Un nom d'entreprise ou de poste vide, ou un contact sans nom, n'est pas envoyé : le
 * champ le dit. Monté sous `key={detail.updated_at}` : une écriture ailleurs relit le formulaire.
 */
export function DetailsForm({ detail, pending, onSave }: DetailsFormProps) {
  const [draft, setDraft] = useState<DetailsDraft>(() => toDraft(detail));
  const [refused, setRefused] = useState(false);
  const patch = changesOf(draft, detail);
  const problem = problemOf(draft);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setRefused(true);
    if (problem !== null || pending) return;
    await onSave(patch);
  }

  return (
    <form noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-3">
      <DetailsFields draft={draft} problem={refused ? problem : null} onChange={setDraft} />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={pending || Object.keys(patch).length === 0}>
          {t(pending ? "applications.drawer.saving" : "applications.drawer.save")}
        </Button>
      </div>
    </form>
  );
}
