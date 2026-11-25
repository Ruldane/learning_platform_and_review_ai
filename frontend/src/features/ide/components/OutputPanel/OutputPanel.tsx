import { useEffect, useId, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { OutputView } from "../viewTypes";

interface OutputPanelProps {
  view: OutputView;
}

/** The status line in full words: never carried by color alone. */
export function statusLine(view: OutputView): string {
  const { status, exitCode, durationMs, kind, origin } = view;
  if (status === "idle") return t("ide.output.idle");
  if (status === "running") return t("ide.output.status.running");
  if (status !== "done") return t(`ide.output.status.${status}`);
  if (kind === "check") {
    if (exitCode !== 0) return t("ide.output.checkFailed");
    // Only your check validates the exercise: Claude's is read, not counted.
    return t(origin === "mcp" ? "ide.output.checkPassedByClaude" : "ide.output.checkPassed");
  }
  return durationMs === null
    ? t("ide.output.status.doneNoTime", { code: exitCode ?? 0 })
    : t("ide.output.status.done", { code: exitCode ?? 0, ms: durationMs });
}

function bodyText(view: OutputView): string {
  if (view.output !== "") return view.output;
  if (view.status === "idle" || view.status === "running") return t("ide.output.waiting");
  return t("ide.output.empty");
}

/**
 * A run's output: read-only (the program does not read the keyboard), with its state
 * as text. When you start a run, focus moves here: this is where the result is read. A
 * run started by Claude is shown the same way, marked « lancée par Claude », without focus.
 */
export function OutputPanel({ view }: OutputPanelProps) {
  const headingId = useId();
  const region = useRef<HTMLElement>(null);
  const { runId, origin } = view;
  useEffect(() => {
    // A run by Claude never takes focus: you may be typing.
    if (runId && origin === "app") region.current?.focus();
  }, [runId, origin]);
  return (
    <section
      ref={region}
      tabIndex={-1}
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 outline-none focus-visible:ring-3 focus-visible:ring-ring"
    >
      <h2 id={headingId} className="font-medium">
        {t("ide.output.title")}
      </h2>
      {origin === "mcp" ? (
        <p className="w-fit rounded-md border border-border bg-muted px-2 py-0.5 text-xs font-medium">
          {t("ide.output.byClaude")}
        </p>
      ) : null}
      <p role="status" className="text-sm">
        {statusLine(view)}
      </p>
      <pre
        role="log"
        aria-live="off"
        aria-label={t("ide.output.label")}
        className="max-h-64 min-h-16 overflow-auto rounded-lg bg-muted p-2 font-mono text-sm whitespace-pre-wrap break-words"
      >
        {bodyText(view)}
      </pre>
      {view.truncated ? <p className="text-sm">{t("ide.output.truncated")}</p> : null}
      {view.error ? (
        <p role="alert" className="text-sm text-destructive">
          {view.error}
        </p>
      ) : null}
      <p className="text-xs text-muted-foreground">{t("ide.output.readonly")}</p>
    </section>
  );
}
