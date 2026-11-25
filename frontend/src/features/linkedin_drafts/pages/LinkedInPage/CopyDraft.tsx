import { useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function CopyDraft({ allowed, read, label }: {
  allowed: boolean;
  read: () => Promise<string>;
  label: string;
}) {
  const [status, setStatus] = useState<"copied" | "copyFailed" | null>(null);
  const copying = useRef(false);
  async function copy() {
    if (!allowed || copying.current) return;
    if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
      setStatus("copyFailed");
      return;
    }
    copying.current = true;
    setStatus(null);
    try {
      const content = read().then((text) => new Blob([text], { type: "text/plain" }));
      // A deferred promise keeps the write inside the user gesture, including in Safari.
      void content.catch(() => undefined);
      const item = new ClipboardItem({ "text/plain": content });
      await Promise.all([navigator.clipboard.write([item]), content]);
      setStatus("copied");
    } catch {
      setStatus("copyFailed");
    } finally {
      copying.current = false;
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
