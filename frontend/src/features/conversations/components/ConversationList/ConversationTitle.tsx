import { useId, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

export function ConversationTitle({
  title,
  busy,
  onSave,
}: {
  title: string;
  busy: boolean;
  onSave: (title: string) => void;
}) {
  const id = useId();
  const [draft, setDraft] = useState({ title, value: title });
  const value = draft.title === title ? draft.value : title;
  const input = useRef<HTMLInputElement>(null);
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        const next = value.trim();
        if (next && next !== title) {
          input.current?.focus();
          onSave(next);
        }
      }}
    >
      <label htmlFor={id} className="text-sm">
        {t("conversations.list.titleField")}
      </label>
      <input
        ref={input}
        id={id}
        className={fieldClass}
        value={value}
        maxLength={120}
        onChange={(event) => setDraft({ title, value: event.target.value })}
      />
      <Button
        size="sm"
        variant="outline"
        disabled={busy || !value.trim() || value.trim() === title}
      >
        {t("conversations.list.rename")}
      </Button>
    </form>
  );
}
