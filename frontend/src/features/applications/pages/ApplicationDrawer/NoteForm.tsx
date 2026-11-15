import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DraftField, type FieldSpec } from "../../components/DraftField";
import type { EventIn } from "../../types";

const NOTE: FieldSpec = {
  key: "note",
  label: t("applications.drawer.noteField"),
  kind: "textarea",
};

interface NoteFormProps {
  pending: boolean;
  onRecord: (event: EventIn) => Promise<boolean>;
}

/** Une note datée dans le fil de la fiche. */
export function NoteForm({ pending, onRecord }: NoteFormProps) {
  const [text, setText] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || text.trim() === "") return;
    if (await onRecord({ kind: "note", text: text.trim() })) setText("");
  }

  return (
    <form noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-2">
      <DraftField spec={NOTE} value={text} onChange={setText} />
      <div>
        <Button type="submit" variant="outline" disabled={pending || text.trim() === ""}>
          {t("applications.drawer.noteAction")}
        </Button>
      </div>
    </form>
  );
}
