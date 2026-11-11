import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface TextTabProps {
  busy: boolean;
  onSubmitText: (title: string, text: string) => void;
}

/** Import d'un texte collé : titre facultatif, texte requis. */
export function TextTab({ busy, onSubmitText }: TextTabProps) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const canSubmit = !busy && text.trim() !== "";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSubmit) onSubmitText(title.trim(), text);
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm font-medium">
        {t("memory.upload.textTitle")}
        <input
          type="text"
          value={title}
          disabled={busy}
          onChange={(event) => setTitle(event.target.value)}
          className={fieldClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        {t("memory.upload.textBody")}
        <textarea
          value={text}
          disabled={busy}
          rows={8}
          onChange={(event) => setText(event.target.value)}
          className={`${fieldClass} h-auto py-1.5`}
        />
      </label>
      <Button type="submit" disabled={!canSubmit} className="self-start">
        {t("memory.upload.textSubmit")}
      </Button>
    </form>
  );
}
