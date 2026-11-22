import { useEffect, useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { RunLog } from "../../components/RunLog";
import { useTerminal } from "../../hooks/useTerminal";
import { TerminalInputForm } from "./TerminalInputForm";

interface Props {
  sessionId: string;
  save: () => Promise<boolean>;
}

export function TerminalPanel({ sessionId, save }: Props) {
  const { progress, action } = useTerminal(sessionId, save);
  const open = useRef<HTMLButtonElement>(null);
  const running = progress?.status === "running";
  useEffect(() => {
    if (progress && !running) open.current?.focus();
  }, [progress, running]);
  return (
    <section className="grid gap-2 rounded-lg border border-border p-3">
      <h2 className="text-sm font-semibold">{t("ide.terminal.title")}</h2>
      <div className="flex flex-wrap gap-2">
        <Button
          ref={open}
          size="sm"
          variant="outline"
          disabled={action.isPending}
          onClick={() => action.mutate({ kind: running ? "stop" : "start" })}
        >
          {t(running ? "ide.terminal.stop" : "ide.terminal.open")}
        </Button>
      </div>
      {progress ? <RunLog label={t("ide.terminal.output")} output={progress.output} /> : null}
      {running ? (
        <TerminalInputForm
          busy={action.isPending}
          send={(data) => action.mutate({ kind: "send", data })}
        />
      ) : null}
      {progress && !running ? (
        <p role="status" className="text-sm">
          {t("ide.terminal.closed")}
        </p>
      ) : null}
      {progress?.error ? <InlineError message={progress.error} /> : null}
      {action.error ? <InlineError message={errorMessage(action.error)} /> : null}
    </section>
  );
}
