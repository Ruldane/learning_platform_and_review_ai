import { Check, Loader2, X } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { ToolCallView } from "@/shared/realtime/types";

interface ToolChipProps {
  call: ToolCallView;
}

/** L'état d'un appel s'écrit toujours en texte : l'icône ne porte jamais seule l'information. */
function callState(ok: boolean | undefined) {
  if (ok === undefined) {
    return {
      Icon: Loader2,
      label: t("session.tool.running"),
      iconClass: "motion-safe:animate-spin",
    };
  }
  return ok
    ? { Icon: Check, label: t("session.tool.ok"), iconClass: "" }
    : { Icon: X, label: t("session.tool.failed"), iconClass: "" };
}

/** Pastille dépliable d'un appel d'outil : nom, état, puis arguments et résumé. */
export function ToolChip({ call }: ToolChipProps) {
  const { Icon, label, iconClass } = callState(call.ok);
  return (
    <details className="rounded-lg border border-border bg-background text-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg px-2.5 py-1 marker:hidden">
        <span className="font-mono text-xs">{call.tool}</span>
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <Icon aria-hidden="true" className={`size-3.5 ${iconClass}`} />
          {label}
        </span>
      </summary>
      <div className="space-y-1 border-t border-border px-2.5 py-2">
        <p className="text-xs font-medium">{t("session.tool.args")}</p>
        <pre className="overflow-x-auto rounded bg-muted p-2 text-xs">
          {JSON.stringify(call.args, null, 2)}
        </pre>
        {call.summary ? (
          <>
            <p className="text-xs font-medium">{t("session.tool.summary")}</p>
            <p>{call.summary}</p>
          </>
        ) : null}
      </div>
    </details>
  );
}
