import { useId, type FormEvent, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { InlineError } from "@/shared/ui/states/InlineError";
import { MAX_TEXT, MAX_URL, detectSource } from "../source";
import type { CaptureSource } from "../viewTypes";
import { FieldNotes } from "./FieldNotes";

interface LinkNoteFormProps {
  /** The typed text (kept outside the dialog: closing does not lose it). */
  value: string;
  onValueChange: (value: string) => void;
  busy: boolean;
  /** The file is being imported: the button keeps its label. */
  uploading: boolean;
  error: string | null;
  onSubmit: (source: CaptureSource) => void;
}

/** The sentence saying how the field will be read: link, note, or the hint while it is empty. */
function hintOf(source: CaptureSource | null): string {
  if (source === null) return t("capture.input.hintEmpty");
  return t(source.kind === "url" ? "capture.input.hintLink" : "capture.input.hintText");
}

/** Ctrl+Enter (or Cmd+Enter) sends, except during a composition (IME). */
const isSendShortcut = (event: KeyboardEvent) =>
  event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing;

/**
 * The single field: a link (a lone `http(s)://` address) or a note. Focus lands there by default.
 * The sentence under the field says how it will be read; a counter shows the 20,000
 * character limit, and a link over 2,048 characters is refused, with a message saying so.
 */
export function LinkNoteForm(props: LinkNoteFormProps) {
  const { value, onValueChange, busy, uploading, error, onSubmit } = props;
  const id = useId();
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
        aria-describedby={`${id}-hint ${id}-count`}
        onChange={(event) => onValueChange(event.target.value)}
        onKeyDown={onKeyDown}
        className={cn(fieldClass, "h-auto min-h-24 py-1.5")}
      />
      <FieldNotes id={id} count={value.length} tooLong={tooLong} hint={hintOf(source)} />
      {error ? <InlineError message={error} /> : null}
      <Button type="submit" disabled={busy || source === null || tooLong} className="self-start">
        {busy && !uploading ? t("capture.input.submitting") : t("capture.input.submit")}
      </Button>
    </form>
  );
}
