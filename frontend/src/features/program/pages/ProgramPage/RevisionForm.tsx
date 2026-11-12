import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface RevisionFormProps {
  busy: boolean;
  /** `true` si la demande est partie (le formulaire se referme). */
  onSend: (note: string) => Promise<boolean>;
  onCancel: () => void;
}

/** La note d'une demande de révision : ce qu'il faut revoir, obligatoire. */
export function RevisionForm({ busy, onSend, onCancel }: RevisionFormProps) {
  const [note, setNote] = useState("");
  const [missing, setMissing] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = note.trim();
    setMissing(text === "");
    if (text !== "" && (await onSend(text))) onCancel();
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-2">
      <label className="flex flex-col gap-1 text-sm font-medium">
        {t("program.validation.noteLabel")}
        <textarea
          value={note}
          rows={3}
          maxLength={2000}
          aria-invalid={missing}
          disabled={busy}
          onChange={(event) => setNote(event.target.value)}
          className="w-full rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm font-normal outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring disabled:opacity-50"
        />
      </label>
      {missing ? (
        <p role="alert" className="text-sm text-destructive">
          {t("program.validation.noteRequired")}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>
          {t("program.validation.send")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t("program.validation.cancel")}
        </Button>
      </div>
    </form>
  );
}
