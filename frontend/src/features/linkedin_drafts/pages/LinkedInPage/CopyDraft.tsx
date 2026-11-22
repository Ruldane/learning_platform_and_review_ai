import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function CopyDraft({ allowed, text, label }: {
  allowed: boolean;
  text: string;
  label: string;
}) {
  const [status, setStatus] = useState<"copied" | "copyFailed" | null>(null);
  async function copy() {
    if (!allowed) return;
    try {
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      setStatus("copyFailed");
    }
  }
  return (
    <div className="grid justify-items-start gap-2">
      <Button type="button" variant="outline" aria-disabled={!allowed} onClick={() => void copy()}>
        {label}
      </Button>
      {status ? <p role="status">{t(`linkedInDrafts.${status}`)}</p> : null}
    </div>
  );
}
