import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { TrialPleading } from "../../components/TrialPleading";
import { VerdictForm } from "../../components/VerdictForm";
import type { CodePleading, TrialVerdict, TrialView } from "../../types";

interface TrialDossierProps {
  data: TrialView;
  busy: boolean;
  onOpen: () => void;
  onVerdict: (verdict: TrialVerdict) => void;
}

function toPleading(pleading: CodePleading) {
  return {
    roleLabel: t(`codeTrial.roles.${pleading.role}`),
    argument: pleading.argument,
    quotes: pleading.citations.map((citation) => ({
      id: `${citation.path}:${citation.start_line}`,
      label: t("codeTrial.citation", {
        path: citation.path,
        from: citation.start_line,
        to: citation.end_line,
      }),
      code: citation.text,
    })),
  };
}

export function TrialDossier({ data, busy, onOpen, onVerdict }: TrialDossierProps) {
  const verdictHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    verdictHeading.current?.focus();
  }, [data.verdict]);
  return (
    <div className="grid gap-4">
      <p className="text-sm font-medium">
        {t(data.file_count === 1 ? "codeTrial.snapshotOne" : "codeTrial.snapshot", {
          version: data.files_version,
          count: data.file_count,
        })}
      </p>
      {data.status === "running" && <p role="status">{t("codeTrial.running")}</p>}
      {data.status === "failed" && <p role="status">{t("codeTrial.failed")}</p>}
      {data.status !== "running" && (!data.current || data.status === "failed") && (
        <Button type="button" className="justify-self-start" disabled={busy} onClick={onOpen}>
          {t(data.current ? "codeTrial.retry" : "codeTrial.newVersion")}
        </Button>
      )}
      {data.pleadings.length > 0 && (
        <div className="grid gap-3 lg:grid-cols-2">
          {data.pleadings.map((pleading) => (
            <TrialPleading key={pleading.role} {...toPleading(pleading)} />
          ))}
        </div>
      )}
      {data.status === "ready" && (
        <VerdictForm busy={busy} onSave={(choice, reason) => onVerdict({ choice, reason })} />
      )}
      {data.verdict && (
        <section
          aria-labelledby="trial-verdict-result"
          className="grid gap-2 rounded-xl border bg-card p-4"
        >
          <h2
            id="trial-verdict-result"
            ref={verdictHeading}
            tabIndex={-1}
            className="text-lg font-semibold"
          >
            {t("codeTrial.savedVerdict")}
          </h2>
          <p className="font-medium">{t(`codeTrial.choices.${data.verdict.choice}`)}</p>
          <p className="whitespace-pre-wrap break-words">{data.verdict.reason}</p>
        </section>
      )}
    </div>
  );
}
