import { useEffect, useId, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { OutputView } from "../viewTypes";

interface OutputPanelProps {
  view: OutputView;
}

/** La ligne d'état en toutes lettres : jamais portée par la seule couleur. */
export function statusLine(view: OutputView): string {
  const { status, exitCode, durationMs, kind } = view;
  if (status === "idle") return t("ide.output.idle");
  if (status === "running") return t("ide.output.status.running");
  if (status !== "done") return t(`ide.output.status.${status}`);
  if (kind === "check") {
    return exitCode === 0 ? t("ide.output.checkPassed") : t("ide.output.checkFailed");
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
 * La sortie d'une exécution : en lecture seule (le programme ne lit pas le clavier), avec son état
 * en texte. Quand une exécution part, le focus vient ici : c'est là qu'on lit le résultat.
 */
export function OutputPanel({ view }: OutputPanelProps) {
  const headingId = useId();
  const region = useRef<HTMLElement>(null);
  const { runId } = view;
  useEffect(() => {
    if (runId) region.current?.focus();
  }, [runId]);
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
