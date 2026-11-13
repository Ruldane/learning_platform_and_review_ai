import { useId, useState, type FormEvent, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { InlineError } from "@/shared/ui/states/InlineError";
import { MAX_TEXT, MAX_URL, detectSource } from "../source";
import type { CaptureSource } from "../viewTypes";

interface LinkNoteFormProps {
  busy: boolean;
  /** Le fichier est en cours d'import : le bouton garde son libellé. */
  uploading: boolean;
  error: string | null;
  onSubmit: (source: CaptureSource) => void;
}

/** La phrase qui dit comment le champ sera lu : lien, note, ou consigne tant qu'il est vide. */
function hintOf(source: CaptureSource | null): string {
  if (source === null) return t("capture.input.hintEmpty");
  return t(source.kind === "url" ? "capture.input.hintLink" : "capture.input.hintText");
}

/** Ctrl+Entrée (ou Cmd+Entrée) envoie, sauf pendant une composition (IME). */
const isSendShortcut = (event: KeyboardEvent) =>
  event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing;

/**
 * Le champ unique : un lien (adresse `http(s)://` seule) ou une note. Le focus y arrive d'office.
 * La phrase sous le champ dit comment il sera lu.
 */
export function LinkNoteForm({ busy, uploading, error, onSubmit }: LinkNoteFormProps) {
  const id = useId();
  const [value, setValue] = useState("");
  const source = detectSource(value);
  const tooLong = source?.kind === "url" ? source.url.length > MAX_URL : false;

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (busy || source === null || tooLong) return;
    onSubmit(source);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!isSendShortcut(event)) return;
    event.preventDefault();
    submit();
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {t("capture.input.label")}
      </label>
      <textarea
        id={id}
        rows={4}
        autoFocus
        value={value}
        maxLength={MAX_TEXT}
        disabled={busy}
        aria-describedby={`${id}-hint`}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={onKeyDown}
        className={cn(fieldClass, "h-auto min-h-24 py-1.5")}
      />
      <p id={`${id}-hint`} role="status" className="text-xs text-muted-foreground">
        {tooLong ? t("capture.input.tooLong") : hintOf(source)}
      </p>
      {error ? <InlineError message={error} /> : null}
      <Button type="submit" disabled={busy || source === null || tooLong} className="self-start">
        {busy && !uploading ? t("capture.input.submitting") : t("capture.input.submit")}
      </Button>
    </form>
  );
}
