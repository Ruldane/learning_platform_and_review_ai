import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface CopyButtonProps {
  text: string;
  label: string;
}

type CopyState = "idle" | "copied" | "failed";

/** Copies `text` to the clipboard; the result is announced, a failure is announced in French. */
export function CopyButton({ text, label }: CopyButtonProps) {
  const [state, setState] = useState<CopyState>("idle");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="outline" size="sm" onClick={() => void copy()}>
        {label}
      </Button>
      <span role="status" className="text-sm text-muted-foreground">
        {state === "copied" ? t("mcp.reveal.copied") : null}
        {state === "failed" ? t("mcp.reveal.copyFailed") : null}
      </span>
    </div>
  );
}
