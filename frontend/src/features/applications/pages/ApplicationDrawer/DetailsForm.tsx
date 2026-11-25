import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ApplicationDetail, ApplicationPatch } from "../../types";
import { changesOf, problemOf, rebase, toDraft, type DetailsDraft } from "./detailsDraft";
import { DetailsFields } from "./DetailsFields";

interface DetailsFormProps {
  detail: ApplicationDetail;
  pending: boolean;
  /** Sends what changed (and announces « Fiche enregistrée. » outside the form, which is
   * remounted). */
  onSave: (patch: ApplicationPatch) => Promise<boolean>;
}

/**
 * The record's editable fields and its contacts, saved at once (`PATCH`, only what
 * changed). A blank company or job name, or a contact without a name, is not sent: the
 * field says so. When the record is re-read (written elsewhere in the drawer), unsaved edits stay.
 */
export function DetailsForm({ detail, pending, onSave }: DetailsFormProps) {
  const [draft, setDraft] = useState<DetailsDraft>(() => toDraft(detail));
  const [refused, setRefused] = useState(false);
  const [seen, setSeen] = useState(detail);
  if (seen !== detail) {
    // The record was re-read: unsaved edits stay, the rest updates.
    setDraft(rebase(draft, toDraft(seen), toDraft(detail)));
    setSeen(detail);
  }
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
