import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { RevisionForm } from "./RevisionForm";
import { StatusBanner } from "./StatusBanner";
import type { ValidationFlow } from "./useValidationFlow";

/** Le bandeau du brouillon : valider le programme ou demander une révision (point d'arrêt n° 3). */
export function ValidationBar({ flow }: { flow: ValidationFlow }) {
  const [revising, setRevising] = useState(false);
  if (flow.phase !== "ready") return <StatusBanner kind={flow.phase} />;
  return (
    <section
      aria-label={t("program.validation.label")}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <p className="text-sm">
        {flow.canRevise ? t("program.validation.intro") : t("program.validation.introNoSession")}
      </p>
      {flow.sessionFailed ? (
        <p className="text-sm text-muted-foreground">{t("program.validation.sessionFailed")}</p>
      ) : null}
      {revising ? (
        <RevisionForm busy={flow.busy} onSend={flow.onRevise} onCancel={() => setRevising(false)} />
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button type="button" disabled={flow.busy} onClick={() => void flow.onValidate()}>
            {t("program.validation.validate")}
          </Button>
          {flow.canRevise ? (
            <Button
              type="button"
              variant="outline"
              disabled={flow.busy}
              onClick={() => setRevising(true)}
            >
              {t("program.validation.revise")}
            </Button>
          ) : null}
        </div>
      )}
      {flow.notice ? (
        <p role="status" className="text-sm">
          {flow.notice}
        </p>
      ) : null}
      {flow.error ? <InlineError message={flow.error} /> : null}
    </section>
  );
}
