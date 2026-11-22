import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function TerminalInputForm({
  busy,
  send,
}: {
  busy: boolean;
  send: (value: string) => void;
}) {
  const [value, setValue] = useState("");
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => input.current?.focus(), []);
  return (
    <form
      className="flex gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy) {
          send(`${value}\n`);
          setValue("");
        }
      }}
    >
      <input
        ref={input}
        aria-label={t("ide.terminal.input")}
        autoComplete="off"
        spellCheck={false}
        className="min-w-0 flex-1 rounded border border-border bg-background px-2 font-mono focus-visible:ring-2 focus-visible:ring-ring"
        value={value}
        maxLength={4095}
        onChange={(event) => setValue(event.target.value)}
      />
      <Button disabled={busy} type="submit" size="sm">
        {t("ide.terminal.send")}
      </Button>
    </form>
  );
}
